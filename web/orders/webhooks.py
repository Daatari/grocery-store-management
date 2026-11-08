import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import PaymentJob


@csrf_exempt  # Stripe's signature authenticates this server-to-server endpoint.
@require_POST
def stripe_event(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    try:
        event = stripe.Webhook.construct_event(request.body, request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET, tolerance=300)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    event = event.to_dict()
    if event.get("livemode") is not False:
        return HttpResponse(status=400)
    if event.get("type") in {"checkout.session.completed", "checkout.session.expired",
                            "checkout.session.async_payment_succeeded", "checkout.session.async_payment_failed"}:
        session = event["data"]["object"]
        # Notifications are hints. The worker retrieves authoritative state from Stripe.
        # Repeated or out-of-order hints cannot finalize a payment twice.
        PaymentJob.objects.filter(provider="stripe", provider_session=session.get("id"), state="queued").update(
            next_attempt=timezone.now())
    return HttpResponse(status=200)
