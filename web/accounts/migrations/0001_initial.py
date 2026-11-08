import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="Customer", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("guest_key", models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
        ("display_name", models.CharField(max_length=100, blank=True)),
        ("email", models.EmailField(max_length=254, blank=True)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("account", models.OneToOneField(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL))])]
