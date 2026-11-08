import os
import secrets
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from catalog.models import Store, Product, Inventory, ManagerAssignment, Warehouse, WarehouseStock
from catalog.ledger import record


class Command(BaseCommand):
    help = "Create two sample stores and customer/manager accounts in an empty catalog."

    def add_arguments(self, parser):
        parser.add_argument("--if-empty", action="store_true")
        parser.add_argument("--quiet", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        names = ["customer", "manager-east", "manager-harbour"]
        if Store.objects.exists() or User.objects.filter(username__in=names).exists():
            if options["if_empty"]:
                return
            raise CommandError("Demo data already exists. Use a fresh database; existing data was not modified.")
        stores = [Store.objects.create(name="East Market", slug="east-market", address="12 Garden Lane"),
                  Store.objects.create(name="Harbour Market", slug="harbour-market", address="48 Harbour Road")]
        warehouse = Warehouse.objects.create(name="Central warehouse", address="90 Supply Road")
        for name, category, price, stock in [("Apples", "Produce", 399, 16), ("Bananas", "Produce", 149, 30),
            ("Sourdough loaf", "Bakery", 549, 12), ("Whole milk", "Dairy", 499, 20),
            ("Free-range eggs", "Dairy", 649, 18), ("Green peas", "Frozen", 299, 24)]:
            product = Product.objects.create(name=name, category=category)
            WarehouseStock.objects.create(warehouse=warehouse, product=product)
            for index, store in enumerate(stores):
                item = Inventory.objects.create(store=store, product=product, price_cents=price + index * 50, stock=stock)
                record(item, "opening_stock", stock_delta=stock)
        for index, name in enumerate(names):
            password = os.environ.get("GROCERY_DEMO_PASSWORD") or secrets.token_urlsafe(18)
            user = User.objects.create_user(username=name, password=password)
            if index:
                ManagerAssignment.objects.create(user=user, store=stores[index - 1])
            if not options["quiet"]:
                self.stdout.write(f"{name}: {password}")
        if not options["quiet"]:
            self.stdout.write("Sample accounts created. Store these demo credentials locally.")
