from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="inventory", name="reserved", field=models.PositiveIntegerField(default=0)),
        migrations.AddConstraint(model_name="inventory", constraint=models.CheckConstraint(
            condition=models.Q(reserved__gte=0, reserved__lte=models.F("stock")), name="valid_reserved_stock")),
        migrations.CreateModel(name="InventoryEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("event_key", models.CharField(max_length=120, unique=True)),
            ("action", models.CharField(max_length=32)),
            ("stock_delta", models.IntegerField(default=0)), ("reserved_delta", models.IntegerField(default=0)),
            ("stock_after", models.PositiveIntegerField()), ("reserved_after", models.PositiveIntegerField()),
            ("reference", models.CharField(blank=True, max_length=100)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ("inventory", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="catalog.inventory"))]),
    ]
