import hashlib
import hmac
import json
import uuid
from django.conf import settings
from .models import Inventory, InventoryEvent


def digest(event):
    payload = {name: getattr(event, name) for name in ("inventory_id", "event_key", "action", "stock_delta",
        "reserved_delta", "stock_after", "reserved_after", "actor_id", "reference", "previous_hash")}
    payload["created_at"] = event.created_at.isoformat()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hmac.new(settings.SECRET_KEY.encode(), ("inventory-ledger-v1\n" + canonical).encode(), hashlib.sha256).hexdigest()


def record(item, action, stock_delta=0, reserved_delta=0, actor=None, reference="", event_key=None):
    """Caller must own the inventory row lock in the same transaction as its mutation."""
    item.refresh_from_db()
    event = InventoryEvent.objects.create(inventory=item, event_key=event_key or uuid.uuid4().hex, action=action,
        stock_delta=stock_delta, reserved_delta=reserved_delta, stock_after=item.stock, reserved_after=item.reserved,
        actor=actor, reference=str(reference), previous_hash=item.audit_head)
    event.event_hash = digest(event)
    event.save(update_fields=["event_hash"])
    Inventory.objects.filter(pk=item.pk).update(audit_head=event.event_hash)
    item.audit_head = event.event_hash
    return event


def verify(item):
    previous = ""
    last = None
    for event in item.events.order_by("pk"):
        if event.previous_hash != previous or not hmac.compare_digest(event.event_hash, digest(event)):
            return False
        previous = event.event_hash
        last = event
    return hmac.compare_digest(previous, item.audit_head) and (
        (last.stock_after, last.reserved_after) == (item.stock, item.reserved) if last else item.stock == item.reserved == 0)
