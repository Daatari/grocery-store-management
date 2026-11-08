import json
import logging
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import connection, transaction
from django.db.models import F, Q
from django.utils import timezone
from catalog.models import Inventory
from catalog.ledger import record
from .models import Cart, Order, PaymentJob
from .payments import PaymentUnavailable, validate_payment
from .services import expire_cart


def event(operation, level, code):
    key = uuid.uuid4().hex
    logging.getLogger("grocery.events").info(json.dumps({"schema_version": 1, "event_id": key, "request_id": key,
        "timestamp": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"), "node": settings.NODE_NAME,
        "service": "payment-worker", "operation": operation, "level": level,
        "outcome": "success" if level == "INFO" else "failure", "code": code, "duration_us": 0}))


@transaction.atomic
def claim():
    now = timezone.now()
    jobs = PaymentJob.objects.filter(Q(state="queued", next_attempt__lte=now) | Q(state="running", lease_until__lte=now)).order_by("pk")
    if connection.features.has_select_for_update_skip_locked:
        jobs = jobs.select_for_update(skip_locked=True)
    else:
        jobs = jobs.select_for_update()
    job = jobs.first()
    if not job:
        return None
    job.state, job.lease_token = "running", uuid.uuid4()
    job.lease_until = now + timedelta(seconds=30)
    job.attempts += 1
    job.save()
    return job


@transaction.atomic
def finish(job_id, lease_token, result=None, error=None):
    initial = PaymentJob.objects.select_related("order").get(pk=job_id)
    cart = Cart.objects.select_for_update().get(pk=initial.order.cart_id)
    job = PaymentJob.objects.select_for_update().select_related("order").get(pk=job_id)
    if job.state != "running" or job.lease_token != lease_token:
        return False  # A newer worker owns the lease; this response is stale.
    order = job.order
    if error:
        job.state = "review" if job.attempts >= 5 else "queued"
        job.next_attempt = timezone.now() + timedelta(seconds=min(60, 2 ** job.attempts))
        job.last_code = error
        if job.state == "review":
            order.status = "needs_review"
            order.save(update_fields=["status"])
        job.save()
        event("payment.retry", "WARN", error)
        return True
    if result["decision"] == "waiting":
        job.provider_session = result["payment_id"]
        job.checkout_url = result["url"]
        job.state, job.attempts = "queued", 0
        job.next_attempt = timezone.now() + timedelta(seconds=15)
        job.save()
        return True
    lines = list(order.lines.order_by("inventory_id"))
    inventory = {row.pk: row for row in Inventory.objects.select_for_update().filter(
        pk__in=[line.inventory_id for line in lines]).order_by("pk")}
    approved = result["decision"] == "approved"
    for line in lines:
        item = inventory[line.inventory_id]
        if item.reserved < line.quantity:
            raise RuntimeError("Reservation invariant violated; operator review required")
        Inventory.objects.filter(pk=item.pk).update(reserved=F("reserved") - line.quantity,
            stock=F("stock") - (line.quantity if approved else 0), version=F("version") + 1)
        record(item, "sale" if approved else "payment_release", stock_delta=-line.quantity if approved else 0,
               reserved_delta=-line.quantity, actor=order.customer.account, reference=str(order.pk), event_key=f"payment:{order.pk}:{item.pk}")
    cart.lines.filter(quantity__gt=0).update(quantity=0, expires_at=None, state="consumed" if approved else "released")
    cart.state = "open"
    cart.save(update_fields=["state"])
    order.status = "confirmed" if approved else "declined"
    order.save(update_fields=["status"])
    job.state, job.last_code, job.provider_reference = "done", order.status, result["payment_id"]
    job.save()
    transaction.on_commit(lambda: event("payment.complete", "INFO", "confirmed" if approved else "declined"))
    return True


def process_one():
    job = claim()
    if not job:
        return False
    try:
        # Network I/O is outside any database transaction or row lock.
        if job.provider == "stripe":
            from .stripe_gateway import validate
            result = validate(job)
        else:
            result = validate_payment(job.order, job.scenario)
    except PaymentUnavailable as error:
        finish(job.pk, job.lease_token, error=str(error))
    else:
        finish(job.pk, job.lease_token, result=result)
    return True


def sweep_expired():
    ids = list(Cart.objects.filter(state="open", lines__quantity__gt=0,
        lines__expires_at__lte=timezone.now()).values_list("pk", flat=True).distinct()[:100])
    for cart_id in ids:
        expire_cart(cart_id)


@transaction.atomic
def retry_review(user, order_id):
    if not user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    order = Order.objects.get(pk=order_id)
    Cart.objects.select_for_update().get(pk=order.cart_id)
    job = PaymentJob.objects.select_for_update().get(order=order)
    if job.state == "review":
        job.state, job.attempts, job.next_attempt = "queued", 0, timezone.now()
        job.save()
        order.status = "pending"
        order.save(update_fields=["status"])
