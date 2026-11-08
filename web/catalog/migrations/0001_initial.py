from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Store", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=100)), ("slug", models.SlugField(unique=True)),
            ("address", models.CharField(max_length=200)), ("is_active", models.BooleanField(default=True))]),
        migrations.CreateModel(name="Product", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=100)), ("category", models.CharField(max_length=80))]),
        migrations.CreateModel(name="ManagerAssignment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="managers", to="catalog.store")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))],
            options={"constraints": [models.UniqueConstraint(fields=("user", "store"), name="unique_store_manager")]}),
        migrations.CreateModel(name="Inventory", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("price_cents", models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(10000000)])),
            ("stock", models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(1000000)])),
            ("version", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)),
            ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="catalog.product")),
            ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory", to="catalog.store"))],
            options={"constraints": [
                models.UniqueConstraint(fields=("store", "product"), name="unique_store_product"),
                models.CheckConstraint(condition=models.Q(price_cents__gte=0, price_cents__lte=10000000), name="valid_inventory_price"),
                models.CheckConstraint(condition=models.Q(stock__gte=0, stock__lte=1000000), name="valid_inventory_stock")]}),
    ]
