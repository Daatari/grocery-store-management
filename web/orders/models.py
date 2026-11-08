import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Cart(models.Model):
    customer = models.ForeignKey("accounts.Customer", on_delete=models.CASCADE)
    store = models.ForeignKey("catalog.Store", on_delete=models.PROTECT)
    state = models.CharField(max_length=16, default="open")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["customer", "store"], name="one_cart_per_customer_store")]


class CartLine(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="lines")
    inventory = models.ForeignKey("catalog.Inventory", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    state = models.CharField(max_length=16, default="held")
    expires_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "inventory"], name="unique_cart_inventory"),
            models.CheckConstraint(condition=Q(quantity__gte=0, quantity__lte=99), name="valid_cart_quantity")]

    def clean(self):
        if self.cart_id and self.inventory_id and self.cart.store_id != self.inventory.store_id:
            raise ValidationError("A cart can contain inventory from only its own store.")

    @property
    def subtotal(self):
        cents = self.quantity * self.inventory.price_cents
        return f"{cents // 100}.{cents % 100:02d}"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey("accounts.Customer", on_delete=models.PROTECT)
    store = models.ForeignKey("catalog.Store", on_delete=models.PROTECT, related_name="orders")
    checkout_key = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    total_cents = models.PositiveBigIntegerField()
    status = models.CharField(max_length=20, default="pending")
    cart = models.ForeignKey(Cart, null=True, on_delete=models.PROTECT)
    contact_name = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    buyer_type = models.CharField(max_length=10, default="account")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["customer", "checkout_key"], name="idempotent_customer_checkout")]

    @property
    def total(self):
        return f"{self.total_cents // 100}.{self.total_cents % 100:02d}"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    inventory = models.ForeignKey("catalog.Inventory", on_delete=models.PROTECT)
    product_name = models.CharField(max_length=100)
    unit_price_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(quantity__gte=1, quantity__lte=99), name="valid_order_quantity")]

    @property
    def subtotal(self):
        cents = self.quantity * self.unit_price_cents
        return f"{cents // 100}.{cents % 100:02d}"


class PaymentJob(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment_job")
    provider = models.CharField(max_length=16, default="simulator")
    checkout_url = models.URLField(max_length=2000, blank=True)
    provider_session = models.CharField(max_length=255, blank=True, unique=True, null=True)
    scenario = models.CharField(max_length=16, default="approve")
    state = models.CharField(max_length=20, default="queued")
    attempts = models.PositiveIntegerField(default=0)
    next_attempt = models.DateTimeField()
    lease_until = models.DateTimeField(null=True)
    lease_token = models.UUIDField(null=True)
    provider_reference = models.CharField(max_length=100, blank=True)
    last_code = models.CharField(max_length=80, blank=True)
