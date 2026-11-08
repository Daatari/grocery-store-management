import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, IntegrityError, transaction
from django.test import Client, TestCase, TransactionTestCase
from catalog.models import Store, Product, Inventory, ManagerAssignment
from catalog.services import update_inventory
from orders.models import Cart, CartLine, Order, OrderLine
from orders.services import set_quantity, checkout
from orders.worker import process_one
def settle():
    with patch("orders.worker.validate_payment", return_value={"decision": "approved", "payment_id": str(uuid.uuid4())}):
        process_one()



class Fixture:
    def make_data(self):
        self.customer = User.objects.create_user("customer", password="Test-password-long-43")
        self.other = User.objects.create_user("other", password="Test-password-long-43")
        self.manager = User.objects.create_user("manager", password="Test-password-long-43")
        self.east = Store.objects.create(name="East", slug="east", address="Garden Lane")
        self.west = Store.objects.create(name="West", slug="west", address="Harbour Road")
        self.product = Product.objects.create(name="Apples", category="Produce")
        self.item = Inventory.objects.create(store=self.east, product=self.product, price_cents=399, stock=5)
        self.west_item = Inventory.objects.create(store=self.west, product=self.product, price_cents=499, stock=8)
        ManagerAssignment.objects.create(user=self.manager, store=self.east)


class ApplicationTests(Fixture, TestCase):
    def setUp(self):
        self.make_data()
        cache.clear()

    def test_store_prices_and_customer_carts_are_separate(self):
        set_quantity(self.customer, self.east, self.item.pk, 2)
        set_quantity(self.customer, self.west, self.west_item.pk, 3)
        set_quantity(self.other, self.east, self.item.pk, 1)
        self.assertEqual(Cart.objects.count(), 3)
        self.client.force_login(self.customer)
        response = self.client.get("/cart/east/")
        self.assertContains(response, "$7.98")
        self.assertNotContains(response, "$14.97")
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 5)  # On-hand stock stays unchanged until payment; availability is reserved.

    def test_cross_store_item_injection_rejected(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.post(f"/cart/east/items/{self.west_item.pk}/", {"quantity": 1}).status_code, 404)
        self.assertEqual(CartLine.objects.count(), 0)

    def test_cart_update_remove_and_invalid_quantity(self):
        set_quantity(self.customer, self.east, self.item.pk, 3)
        set_quantity(self.customer, self.east, self.item.pk, 1, replace=True)
        self.assertEqual(CartLine.objects.get().quantity, 1)
        with self.assertRaises(ValidationError):
            set_quantity(self.customer, self.east, self.item.pk, 99)
        set_quantity(self.customer, self.east, self.item.pk, 0, replace=True)
        self.assertEqual(CartLine.objects.get().quantity, 0)

    def test_checkout_atomic_idempotent_and_snapshots(self):
        set_quantity(self.customer, self.east, self.item.pk, 2)
        key = uuid.uuid4()
        order = checkout(self.customer, self.east, key)
        self.assertEqual(checkout(self.customer, self.east, key).pk, order.pk)
        settle()
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 3)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.total_cents, 798)
        self.assertEqual(CartLine.objects.get().quantity, 0)
        self.product.name = "New name"
        self.product.save()
        self.item.price_cents = 999
        self.item.save()
        self.assertEqual(order.lines.get().product_name, "Apples")
        self.assertEqual(order.lines.get().unit_price_cents, 399)

    def test_failure_rolls_back_stock_order_and_cart(self):
        set_quantity(self.customer, self.east, self.item.pk, 2)
        with patch("orders.services.OrderLine.objects.create", side_effect=RuntimeError("injected failure")):
            with self.assertRaises(RuntimeError):
                checkout(self.customer, self.east, uuid.uuid4())
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 5)
        self.assertEqual(CartLine.objects.get().quantity, 2)
        self.assertFalse(Order.objects.exists())

    def test_stock_changes_rechecked_at_checkout(self):
        set_quantity(self.customer, self.east, self.item.pk, 4)
        Inventory.objects.filter(pk=self.item.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            checkout(self.customer, self.east, uuid.uuid4())
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartLine.objects.get().quantity, 4)

    def test_manager_cannot_cross_store_or_customer_boundary(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get("/manage/east/").status_code, 200)
        self.assertEqual(self.client.get("/manage/west/").status_code, 403)
        self.assertEqual(self.client.post(f"/manage/west/inventory/{self.west_item.pk}/",
            {"price_cents": 1, "stock": 1, "version": 0, "is_active": "on"}).status_code, 403)
        with self.assertRaises(PermissionDenied):
            update_inventory(self.customer, "east", self.item.pk, price_cents=1, stock=1, version=0, is_active=True)

    def test_stale_manager_edit_does_not_overwrite_checkout(self):
        set_quantity(self.customer, self.east, self.item.pk, 1)
        checkout(self.customer, self.east, uuid.uuid4())
        settle()
        with self.assertRaises(ValidationError):
            update_inventory(self.manager, "east", self.item.pk, price_cents=1, stock=100, version=0, is_active=True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 4)
        update_inventory(self.manager, "east", self.item.pk, price_cents=450, stock=10, version=self.item.version, is_active=True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.price_cents, 450)

    def test_private_order_is_not_visible_to_other_customer(self):
        set_quantity(self.customer, self.east, self.item.pk, 1)
        order = checkout(self.customer, self.east, uuid.uuid4())
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/orders/{order.pk}/").status_code, 404)

    def test_database_rejects_negative_stock_and_duplicate_listing(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inventory.objects.filter(pk=self.item.pk).update(stock=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inventory.objects.create(store=self.east, product=self.product, price_cents=1, stock=1)

    def test_csrf_required_and_get_cannot_mutate(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.customer)
        self.assertEqual(client.post(f"/cart/east/items/{self.item.pk}/", {"quantity": 1}).status_code, 403)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(f"/cart/east/items/{self.item.pk}/").status_code, 405)

    def test_registration_cannot_grant_staff_or_manager(self):
        response = self.client.post("/accounts/register/", {"username": "newcustomer", "password1": "Fresh-password-73!",
            "password2": "Fresh-password-73!", "is_staff": "true", "is_superuser": "true"})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newcustomer")
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertFalse(ManagerAssignment.objects.filter(user=user).exists())

    def test_api_and_templates(self):
        self.assertEqual(self.client.get("/api/stores/").json()["stores"][0]["name"], "East")
        self.assertEqual(self.client.get("/api/stores/east/inventory/").json()["inventory"][0]["price_cents"], 399)
        for path in ["/", "/stores/east/", "/accounts/login/", "/accounts/register/"]:
            self.assertEqual(self.client.get(path).status_code, 200)
        self.client.force_login(self.customer)
        for path in ["/cart/east/", "/orders/", "/manage/"]:
            self.assertEqual(self.client.get(path).status_code, 200)


class ConcurrentCheckoutTests(Fixture, TransactionTestCase):
    def setUp(self):
        self.make_data()

    def test_two_customers_cannot_buy_the_last_unit(self):
        if connection.vendor != "postgresql":
            self.skipTest("Threaded row-lock test runs against PostgreSQL in CI.")
        Inventory.objects.filter(pk=self.item.pk).update(stock=1)
        barrier = Barrier(2)
        def buy(user_id):
            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                store = Store.objects.get(pk=self.east.pk)
                barrier.wait(timeout=10)
                try:
                    set_quantity(user, store, self.item.pk, 1)
                    return "placed"
                except ValidationError:
                    return "rejected"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(buy, [self.customer.pk, self.other.pk]))
        self.assertCountEqual(results, ["placed", "rejected"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 1)
        self.assertEqual(self.item.reserved, 1)
        self.assertEqual(Order.objects.count(), 0)
