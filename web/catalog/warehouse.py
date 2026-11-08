from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import WarehouseStock, WarehouseMovement, Inventory
from .ledger import record

@transaction.atomic
def move(user, stock_id, quantity, key, destination_id=None):
    if not user.is_superuser:
        raise PermissionDenied
    if type(quantity) is not int or not 1 <= quantity <= 1000000:
        raise ValidationError("Quantity must be between 1 and 1,000,000.")
    stock = WarehouseStock.objects.select_for_update().get(pk=stock_id)
    previous = WarehouseMovement.objects.filter(request_key=key).first()
    delta = -quantity if destination_id else quantity
    if previous:
        if (previous.stock_id, previous.destination_id, previous.delta) != (stock_id, destination_id, delta):
            raise ValidationError("Request key belongs to a different movement.")
        return previous
    if not 0 <= stock.quantity + delta <= 1000000:
        raise ValidationError("Insufficient stock or warehouse capacity exceeded.")
    if destination_id:
        item = Inventory.objects.select_for_update().get(pk=destination_id, product_id=stock.product_id)
        if item.stock + quantity > 1000000:
            raise ValidationError("Store capacity exceeded.")
        item.stock += quantity
        item.version += 1
        item.save(update_fields=["stock", "version"])
        record(item, "warehouse_receipt", stock_delta=quantity, actor=user, reference=str(key), event_key=f"transfer:{key}")
    stock.quantity += delta
    stock.save(update_fields=["quantity"])
    return WarehouseMovement.objects.create(stock=stock, destination_id=destination_id, request_key=key,
        delta=delta, quantity_after=stock.quantity, actor=user)
