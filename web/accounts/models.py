import uuid
from django.conf import settings
from django.db import models

class Customer(models.Model):
    # Login credentials belong to User. Guests have no login or synthetic password.
    account = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    guest_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    display_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_guest(self):
        return self.account_id is None
