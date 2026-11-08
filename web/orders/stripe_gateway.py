"""Test-only hosted Checkout adapter. No card data enters this application."""
from datetime import timedelta
from urllib.parse import urlparse
import stripe
from django.conf import settings
from django.utils import timezone
from .payments import PaymentUnavailable


def client():
    if not settings.STRIPE_SECRET_KEY.startswith("sk_test_"):
        raise PaymentUnavailable("stripe_not_configured")
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY, max_network_retries=1,
        http_client=stripe.RequestsClient(timeout=8))


def validate(job):
    order = job.order
    api = client()
    try:
        if job.provider_session:
            session = api.v1.checkout.sessions.retrieve(job.provider_session)
        else:
            # Never recreate an uncertain session after Stripe's idempotency retention.
            if timezone.now() > order.created_at + timedelta(minutes=89):
                raise PaymentUnavailable("stripe_creation_window_closed")
            session = api.v1.checkout.sessions.create({
                "mode": "payment", "payment_method_types": ["card"],
                "client_reference_id": str(order.pk), "metadata": {"order_id": str(order.pk)},
                "success_url": f"{settings.PUBLIC_BASE_URL}/orders/{order.pk}/",
                "cancel_url": f"{settings.PUBLIC_BASE_URL}/orders/{order.pk}/",
                # Fixed expiry and payload preserve the idempotency key across retries.
                "expires_at": int((order.created_at + timedelta(hours=2)).timestamp()),
                "line_items": [{"price_data": {"currency": "cad", "unit_amount": line.unit_price_cents,
                    "product_data": {"name": line.product_name}}, "quantity": line.quantity}
                    for line in order.lines.order_by("pk")],
                **({"customer_email": order.contact_email} if order.contact_email else {}),
            }, options={"idempotency_key": f"checkout:{order.pk}"})
        if (session.livemode is not False or session.client_reference_id != str(order.pk)
                or session.amount_total != order.total_cents or session.currency != "cad"):
            raise PaymentUnavailable("stripe_session_mismatch")
        if session.payment_status == "paid":
            return {"decision": "approved", "payment_id": session.id}
        if session.status == "expired" and session.payment_status == "unpaid":
            return {"decision": "declined", "payment_id": session.id}
        url = session.url or ""
        if url and (urlparse(url).scheme != "https" or urlparse(url).hostname != "checkout.stripe.com"):
            raise PaymentUnavailable("stripe_url_invalid")
        return {"decision": "waiting", "payment_id": session.id, "url": url}
    except (stripe.StripeError, AttributeError, TypeError, ValueError):
        # Do not leak provider messages, customer data, or keys into application logs.
        raise PaymentUnavailable("stripe_unavailable") from None
