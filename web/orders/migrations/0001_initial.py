import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0001_initial"), ("catalog", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Cart", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="accounts.customer")),
            ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="catalog.store"))],
            options={"constraints": [models.UniqueConstraint(fields=("customer", "store"), name="one_cart_per_customer_store")]}),
        migrations.CreateModel(name="CartLine", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("quantity", models.PositiveIntegerField()),
            ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="orders.cart")),
            ("inventory", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="catalog.inventory"))],
            options={"constraints": [
                models.UniqueConstraint(fields=("cart", "inventory"), name="unique_cart_inventory"),
                models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=99), name="valid_cart_quantity")]}),
        migrations.CreateModel(name="Order", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("checkout_key", models.UUIDField()), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("total_cents", models.PositiveBigIntegerField()),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="accounts.customer")),
            ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="catalog.store"))],
            options={"constraints": [models.UniqueConstraint(fields=("customer", "checkout_key"), name="idempotent_customer_checkout")]}),
        migrations.CreateModel(name="OrderLine", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("product_name", models.CharField(max_length=100)), ("unit_price_cents", models.PositiveIntegerField()),
            ("quantity", models.PositiveIntegerField()),
            ("inventory", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="catalog.inventory")),
            ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="orders.order"))],
            options={"constraints": [models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=99), name="valid_order_quantity")]}),
    ]
