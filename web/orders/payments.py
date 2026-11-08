"""A signed, idempotent adapter to the internal payment simulator; no real payments."""
import hashlib
import hmac
import json
import urllib.error
import urllib.request
import uuid
from django.conf import settings


class PaymentUnavailable(Exception):
    pass


def validate_payment(order, scenario):
    if len(settings.PAYMENT_TOKEN) < 32:
        raise PaymentUnavailable("provider_not_configured")
    payload = json.dumps({"key": str(order.pk), "amount_cents": order.total_cents, "scenario": scenario},
                         sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(settings.PAYMENT_TOKEN.encode(), payload, hashlib.sha256).hexdigest()
    request = urllib.request.Request(settings.PAYMENT_URL + "/validate", data=payload,
                                    headers={"Content-Type": "application/json", "X-Signature": signature})
    try:
        with urllib.request.urlopen(request, timeout=settings.PAYMENT_TIMEOUT) as response:
            body = response.read(8193)
            if len(body) > 8192:
                raise PaymentUnavailable("invalid_provider_response")
            expected = hmac.new(settings.PAYMENT_TOKEN.encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, response.headers.get("X-Signature", "")):
                raise PaymentUnavailable("invalid_response_signature")
        result = json.loads(body)
        if not isinstance(result, dict) or not isinstance(result.get("payment_id"), str):
            raise PaymentUnavailable("invalid_provider_response")
        if result.get("key") != str(order.pk) or type(result.get("amount_cents")) is not int or result["amount_cents"] != order.total_cents:
            raise PaymentUnavailable("response_identity_mismatch")
        if result.get("decision") not in ("approved", "declined"):
            raise PaymentUnavailable("invalid_provider_decision")
        uuid.UUID(result["payment_id"])
        return result
    except PaymentUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise PaymentUnavailable("provider_unavailable") from error
