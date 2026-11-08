from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_reservations_ledger")]
    operations = [migrations.AddField(model_name="inventory", name="audit_head", field=models.CharField(blank=True, max_length=64)),
                  migrations.AddField(model_name="inventoryevent", name="previous_hash", field=models.CharField(blank=True, max_length=64)),
                  migrations.AddField(model_name="inventoryevent", name="event_hash", field=models.CharField(blank=True, max_length=64))]
