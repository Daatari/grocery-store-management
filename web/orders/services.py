import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from catalog.models import Inventory, Store
from catalog.ledger import record
from accounts.customers import customer_for
from .models import Cart, CartLine, Order, OrderLine, PaymentJob


def authenticated(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied


def expire_locked(cart):
    if cart.state != "open":
        return
    for line in cart.lines.filter(quantity__gt=0, expires_at__lte=timezone.now()).order_by("inventory_id"):
        item = Inventory.objects.select_for_update().get(pk=line.inventory_id)
        Inventory.objects.filter(pk=item.pk).update(reserved=F("reserved") - line.quantity, version=F("version") + 1)
        record(item, "reservation_expired", reserved_delta=-line.quantity, actor=cart.customer.account, reference=f"cart:{cart.pk}")
        line.quantity, line.state, line.expires_at = 0, "expired", None
        line.save()


def lock_cart_inventory(cart, extra=None):
    ids = list(cart.lines.filter(quantity__gt=0).values_list("inventory_id", flat=True))
    if extra is not None:
        ids.append(extra)
    list(Inventory.objects.select_for_update().filter(pk__in=ids).order_by("pk"))


@transaction.atomic
def expire_cart(cart_id):
    cart = Cart.objects.select_for_update().get(pk=cart_id)
    expire_locked(cart)


@transaction.atomic
def set_quantity(user, store, inventory_id, quantity, *, replace=False):
    user = customer_for(user)
    if type(quantity) is not int or not 0 <= quantity <= 99:
        raise ValidationError("Quantity must be between 0 and 99.")
    if not Store.objects.filter(pk=store.pk, is_active=True).exists():
        raise ValidationError("Store is unavailable.")
    cart, _ = Cart.objects.get_or_create(customer=user, store=store)
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    if cart.state != "open":
        raise ValidationError("This cart is awaiting payment validation. Its reservations are protected.")
    lock_cart_inventory(cart, inventory_id)
    expire_locked(cart)
    item = Inventory.objects.select_for_update().get(pk=inventory_id, store=store)
    line = CartLine.objects.filter(cart=cart, inventory=item).first()
    old = line.quantity if line else 0
    count = quantity if replace else quantity + old
    delta = count - old
    if count > 99 or (delta > 0 and (not item.is_active or delta > item.available)):
        raise ValidationError("That quantity is not available. Choose a smaller quantity.")
    if delta:
        changed = Inventory.objects.filter(pk=item.pk, reserved__gte=max(0, -delta)).filter(
            stock__gte=F("reserved") + delta).update(reserved=F("reserved") + delta, version=F("version") + 1)
        if not changed:
            raise ValidationError("Availability changed. Please try again.")
        record(item, "reserve" if delta > 0 else "release", reserved_delta=delta, actor=user.account, reference=f"cart:{cart.pk}")
    CartLine.objects.update_or_create(cart=cart, inventory=item, defaults={
        "quantity": count, "state": "held" if count else "released",
        "expires_at": timezone.now() + timedelta(seconds=settings.RESERVATION_SECONDS) if count else None})


@transaction.atomic
def checkout(user, store, checkout_key, scenario="approve", provider="simulator", contact_name="", contact_email=""):
    user = customer_for(user)
    if scenario not in ("approve", "decline", "timeout"):
        raise ValidationError("Unknown payment simulation.")
    cart = Cart.objects.select_for_update().filter(customer=user, store=store).first()
    previous = Order.objects.filter(customer=user, checkout_key=checkout_key).first()
    if previous:
        if previous.store_id != store.pk:
            raise ValidationError("Checkout key belongs to another store.")
        return previous
    if not Store.objects.filter(pk=store.pk, is_active=True).exists():
        raise ValidationError("Store is unavailable.")
    if not cart or cart.state != "open":
        raise ValidationError("Cart is empty or already processing.")
    lock_cart_inventory(cart)
    expire_locked(cart)
    lines = list(cart.lines.filter(quantity__gt=0).select_related("inventory__product").order_by("inventory_id"))
    if not lines:
        raise ValidationError("Your cart is empty or its reservations expired.")
    stock = {row.pk: row for row in Inventory.objects.select_for_update().filter(
        pk__in=[line.inventory_id for line in lines], store=store).order_by("pk")}
    total = 0
    for line in lines:
        item = stock.get(line.inventory_id)
        if not item or not item.is_active or item.reserved < line.quantity:
            raise ValidationError("Inventory is unavailable. Release or update your cart.")
        total += item.price_cents * line.quantity
    if provider not in ("simulator", "stripe") or (provider == "stripe" and not settings.STRIPE_SECRET_KEY.startswith("sk_test_")):
        raise ValidationError("This payment provider is not configured.")
    if total > 99999999 or (provider == "stripe" and total < 50):
        raise ValidationError("Order total is outside the payment adapter's supported range.")
    order = Order.objects.create(customer=user, store=store, checkout_key=checkout_key, total_cents=total, cart=cart,
        contact_name=contact_name, contact_email=contact_email, buyer_type="guest" if user.is_guest else "account")
    for line in lines:
        item = stock[line.inventory_id]
        OrderLine.objects.create(order=order, inventory=item, product_name=item.product.name,
                                 unit_price_cents=item.price_cents, quantity=line.quantity)
        line.state, line.expires_at = "processing", None
        line.save()
    cart.state = "processing"
    cart.save(update_fields=["state"])
    # Durable outbox row and the order commit together; no network inside this transaction.
    PaymentJob.objects.create(order=order, provider=provider, scenario=scenario, next_attempt=timezone.now())
    return order
