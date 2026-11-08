from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial"), ("catalog", "0002_reservations_ledger")]
    operations = [
        migrations.AddField(model_name="cart", name="state", field=models.CharField(default="open", max_length=16)),
        migrations.AddField(model_name="cartline", name="state", field=models.CharField(default="held", max_length=16)),
        migrations.AddField(model_name="cartline", name="expires_at", field=models.DateTimeField(null=True)),
        migrations.RemoveConstraint(model_name="cartline", name="valid_cart_quantity"),
        migrations.AddConstraint(model_name="cartline", constraint=models.CheckConstraint(
            condition=models.Q(quantity__gte=0, quantity__lte=99), name="valid_cart_quantity")),
        migrations.AddField(model_name="order", name="status", field=models.CharField(default="pending", max_length=20)),
        migrations.AddField(model_name="order", name="cart", field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="orders.cart")),
        migrations.CreateModel(name="PaymentJob", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("scenario", models.CharField(default="approve", max_length=16)),
            ("state", models.CharField(default="queued", max_length=20)),
            ("attempts", models.PositiveIntegerField(default=0)), ("next_attempt", models.DateTimeField()),
            ("lease_until", models.DateTimeField(null=True)), ("lease_token", models.UUIDField(null=True)),
            ("provider_reference", models.CharField(blank=True, max_length=100)),
            ("last_code", models.CharField(blank=True, max_length=80)),
            ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="payment_job", to="orders.order"))]),
    ]
