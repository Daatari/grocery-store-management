from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F
from django.db import transaction
from .ledger import record
from .models import Inventory, ManagerAssignment, Store


def managed_store(user, slug):
    if not user.is_authenticated:
        raise PermissionDenied
    store = Store.objects.get(slug=slug, is_active=True)
    if not user.is_superuser and not ManagerAssignment.objects.filter(user=user, store=store).exists():
        raise PermissionDenied("You are not a manager for this store.")
    return store


@transaction.atomic
def update_inventory(user, slug, pk, *, price_cents, stock, version, is_active):
    store = managed_store(user, slug)
    if type(price_cents) is not int or not 0 <= price_cents <= 10000000:
        raise ValidationError("Price is outside the supported range.")
    if type(stock) is not int or not 0 <= stock <= 1000000:
        raise ValidationError("Stock is outside the supported range.")
    item = Inventory.objects.select_for_update().get(pk=pk, store=store)
    if stock < item.reserved:
        raise ValidationError("Stock cannot be reduced below active reservations.")
    before = item.stock
    changed = Inventory.objects.filter(pk=pk, store=store, version=version).update(
        price_cents=price_cents, stock=stock, is_active=is_active, version=F("version") + 1)
    if not changed:
        raise ValidationError("Inventory changed while you were editing. Reload and try again.")
    record(item, "manager_adjustment", stock_delta=stock - before, actor=user)
