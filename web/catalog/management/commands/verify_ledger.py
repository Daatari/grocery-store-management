from django.core.management.base import BaseCommand, CommandError
from catalog.models import Inventory
from catalog.ledger import verify


class Command(BaseCommand):
    help = "Check every inventory event hash chain against its current head."

    def handle(self, *args, **options):
        invalid = [item.pk for item in Inventory.objects.all() if not verify(item)]
        if invalid:
            raise CommandError(f"Integrity check failed for inventory IDs: {invalid}")
        self.stdout.write("All inventory event chains verified.")
