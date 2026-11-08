from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion as d
def identity():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))
class Migration(migrations.Migration):
    dependencies = [("catalog", "0003_event_integrity")]
    operations = [
        migrations.CreateModel(name="ProductSource", fields=[identity(),
            ("product", models.OneToOneField(to="catalog.product", on_delete=d.PROTECT, related_name="source")),
            ("provider", models.CharField(max_length=32, default="openfoodfacts")),
            ("barcode", models.CharField(max_length=14, unique=True)),
            ("brand", models.CharField(max_length=120, blank=True)),
            ("package_quantity", models.CharField(max_length=80, blank=True)),
            ("ingredients", models.TextField(blank=True)),
            ("allergens", models.JSONField(default=list)), ("nutrients", models.JSONField(default=dict)),
            ("imported_at", models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name="ProviderQuota", fields=[
            ("name", models.CharField(max_length=32, primary_key=True, serialize=False)),
            ("started_at", models.DateTimeField()), ("count", models.PositiveIntegerField(default=0))]),
        migrations.CreateModel(name="Warehouse", fields=[identity(),
            ("name", models.CharField(max_length=100)), ("address", models.CharField(max_length=200))]),
        migrations.CreateModel(name="WarehouseStock", fields=[identity(),
            ("warehouse", models.ForeignKey(to="catalog.warehouse", on_delete=d.PROTECT)),
            ("product", models.ForeignKey(to="catalog.product", on_delete=d.PROTECT)),
            ("quantity", models.PositiveIntegerField(default=0))], options={"constraints": [
                models.UniqueConstraint(fields=("warehouse", "product"), name="warehouse_product"),
                models.CheckConstraint(condition=models.Q(quantity__gte=0, quantity__lte=1000000), name="warehouse_stock_range")]}),
        migrations.CreateModel(name="WarehouseMovement", fields=[identity(),
            ("stock", models.ForeignKey(to="catalog.warehousestock", on_delete=d.PROTECT, related_name="movements")),
            ("destination", models.ForeignKey(to="catalog.inventory", null=True, blank=True, on_delete=d.PROTECT)),
            ("request_key", models.UUIDField(unique=True)), ("delta", models.IntegerField()),
            ("quantity_after", models.PositiveIntegerField()),
            ("actor", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=d.PROTECT)),
            ("created_at", models.DateTimeField(auto_now_add=True))]),
    ]
