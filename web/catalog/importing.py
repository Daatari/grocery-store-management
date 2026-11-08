from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Product, ProductSource, Inventory
from .services import managed_store
from .ledger import record

@transaction.atomic
def add_listing(user, slug, *, name, category, price_cents, stock, token=""):
    store = managed_store(user, slug)
    if token:
        try:
            data = signing.loads(token, salt="catalog-preview", max_age=900)
        except signing.BadSignature:
            raise ValidationError("Preview expired or was modified. Search again.") from None
        # Lock the store to serialize duplicate import requests for this store.
        type(store).objects.select_for_update().get(pk=store.pk)
        source = ProductSource.objects.filter(barcode=data["barcode"]).first()
        if source:
            product = source.product
        else:
            # Barcode uniqueness also protects concurrent imports across stores.
            product = Product.objects.create(name=data.pop("name"), category=data.pop("category"))
            ProductSource.objects.create(product=product, **data)
    else:
        product = Product(name=name, category=category)
        product.full_clean()
        product.save()
    if Inventory.objects.filter(store=store, product=product).exists():
        raise ValidationError("This product is already listed. Edit its existing inventory instead.")
    item = Inventory(store=store, product=product, price_cents=price_cents, stock=stock)
    item.full_clean()
    item.save()
    record(item, "opening_stock", stock_delta=stock, actor=user)
    return item
