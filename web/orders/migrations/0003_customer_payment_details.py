from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [("orders", "0002_payment_jobs")]
    operations = [
        migrations.AddField(model_name="order", name="contact_name", field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name="order", name="contact_email", field=models.EmailField(max_length=254, blank=True)),
        migrations.AddField(model_name="order", name="buyer_type", field=models.CharField(max_length=10, default="account")),
        migrations.AddField(model_name="paymentjob", name="provider", field=models.CharField(max_length=16, default="simulator")),
        migrations.AddField(model_name="paymentjob", name="checkout_url", field=models.URLField(max_length=2000, blank=True)),
        migrations.AddField(model_name="paymentjob", name="provider_session", field=models.CharField(max_length=255, blank=True, null=True, unique=True)),
    ]
