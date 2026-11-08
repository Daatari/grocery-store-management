from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q


class Store(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    address = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ManagerAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="managers")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "store"], name="unique_store_manager")]


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="inventory")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price_cents = models.PositiveIntegerField(validators=[MaxValueValidator(10000000)])
    stock = models.PositiveIntegerField(validators=[MaxValueValidator(1000000)])
    reserved = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=0)
    audit_head = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["store", "product"], name="unique_store_product"),
            models.CheckConstraint(condition=Q(price_cents__gte=0, price_cents__lte=10000000), name="valid_inventory_price"),
            models.CheckConstraint(condition=Q(stock__gte=0, stock__lte=1000000), name="valid_inventory_stock"),
            models.CheckConstraint(condition=Q(reserved__gte=0, reserved__lte=models.F("stock")), name="valid_reserved_stock"),
        ]

    def __str__(self):
        return f"{self.store.name}: {self.product.name}"

    @property
    def price(self):
        return f"{self.price_cents // 100}.{self.price_cents % 100:02d}"

    @property
    def available(self):
        return self.stock - self.reserved


class InventoryEvent(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name="events")
    event_key = models.CharField(max_length=120, unique=True)
    action = models.CharField(max_length=32)
    stock_delta = models.IntegerField(default=0)
    reserved_delta = models.IntegerField(default=0)
    stock_after = models.PositiveIntegerField()
    reserved_after = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    previous_hash = models.CharField(max_length=64, blank=True)
    event_hash = models.CharField(max_length=64, blank=True)


class ProductSource(models.Model):
    product = models.OneToOneField(Product, on_delete=models.PROTECT, related_name="source")
    provider = models.CharField(max_length=32, default="openfoodfacts")
    barcode = models.CharField(max_length=14, unique=True)
    brand = models.CharField(max_length=120, blank=True)
    package_quantity = models.CharField(max_length=80, blank=True)
    ingredients = models.TextField(blank=True)
    allergens = models.JSONField(default=list)
    nutrients = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now_add=True)

    @property
    def source_url(self):
        return "https://world.openfoodfacts.org/product/" + self.barcode

class ProviderQuota(models.Model):
    name = models.CharField(max_length=32, primary_key=True)
    started_at = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)

class WarehouseStock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.warehouse.name}: {self.product.name}"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["warehouse", "product"], name="warehouse_product"),
            models.CheckConstraint(condition=Q(quantity__gte=0, quantity__lte=1000000), name="warehouse_stock_range")]

class WarehouseMovement(models.Model):
    stock = models.ForeignKey(WarehouseStock, on_delete=models.PROTECT, related_name="movements")
    destination = models.ForeignKey(Inventory, null=True, blank=True, on_delete=models.PROTECT)
    request_key = models.UUIDField(unique=True)
    delta = models.IntegerField()
    quantity_after = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
