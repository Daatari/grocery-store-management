import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the initial deployment administrator without changing existing accounts."

    def handle(self, *args, **options):
        username = os.environ.get("GROCERY_ADMIN_USER", "admin")
        password = os.environ.get("GROCERY_ADMIN_PASSWORD")
        if not password or len(password) < 16:
            raise CommandError("Set GROCERY_ADMIN_PASSWORD to at least 16 characters.")
        existing = User.objects.filter(username=username).first()
        if existing:
            if not existing.is_superuser:
                raise CommandError("The requested administrator username belongs to a non-admin account.")
            self.stdout.write("Administrator already exists; password unchanged.")
            return
        User.objects.create_superuser(username=username, password=password)
        self.stdout.write("Administrator created.")
