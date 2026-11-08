import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from accounts.models import Customer
from catalog.models import Inventory, InventoryEvent, ProductSource, Warehouse, WarehouseStock
from catalog.importing import add_listing
from catalog.providers import normalize, quota
from catalog.ledger import record, verify
from catalog.warehouse import move
from orders.models import CartLine, Cart, PaymentJob
from orders.services import checkout, set_quantity, expire_cart
from orders.worker import claim, finish, process_one
from orders.payments import PaymentUnavailable
from .test_application import Fixture

class ExtensionTests(Fixture, TestCase):
    def setUp(self):
        self.make_data()
        record(self.item, "opening_stock", stock_delta=5)

    def test_expiry_releases_but_processing_never_expires(self):
        set_quantity(self.customer, self.east, self.item.pk, 2)
        CartLine.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        expire_cart(Cart.objects.get().pk)
        self.item.refresh_from_db()
        self.assertEqual(self.item.reserved, 0)
        set_quantity(self.customer, self.east, self.item.pk, 2)
        checkout(self.customer, self.east, uuid.uuid4())
        CartLine.objects.update(expires_at=timezone.now()-timedelta(days=1))
        expire_cart(Cart.objects.get().pk)
        with self.assertRaises(ValidationError):
            set_quantity(self.customer, self.east, self.item.pk, 0, replace=True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.reserved, 2)

    def test_retry_duplicate_and_stale_worker_cannot_double_sell(self):
        set_quantity(self.customer, self.east, self.item.pk, 2)
        order = checkout(self.customer, self.east, uuid.uuid4())
        job = claim()
        self.assertFalse(finish(job.pk, uuid.uuid4(), result={"decision":"approved", "payment_id":"x"}))
        finish(job.pk, job.lease_token, error="timeout")
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.reserved), (5, 2))
        PaymentJob.objects.update(next_attempt=timezone.now())
        new = claim()
        result = {"decision":"approved", "payment_id":"x"}
        finish(new.pk, new.lease_token, result=result)
        self.assertFalse(finish(new.pk, new.lease_token, result=result))
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.reserved), (3, 0))
        self.assertTrue(verify(self.item))
        InventoryEvent.objects.filter(inventory=self.item, action="sale").update(stock_delta=-99)
        self.assertFalse(verify(self.item))

    def test_decline_releases_without_reducing_stock(self):
        set_quantity(self.customer, self.east, self.item.pk, 2)
        checkout(self.customer, self.east, uuid.uuid4(), "decline")
        job = claim()
        finish(job.pk, job.lease_token, result={"decision":"declined", "payment_id":"x"})
        self.item.refresh_from_db()
        self.assertEqual((self.item.stock, self.item.reserved), (5, 0))

    def test_guest_order_private_to_session_and_no_login_account(self):
        self.client.post(f"/cart/east/items/{self.item.pk}/", {"quantity":1})
        response = self.client.post("/cart/east/checkout/", {"checkout_key":uuid.uuid4(), "scenario":"approve",
            "provider":"simulator", "contact_name":"Guest", "contact_email":"guest@example.test"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.assertEqual(Client().get(response.url).status_code, 404)
        order = PaymentJob.objects.get().order
        self.assertIsNone(order.customer.account_id)
        self.assertEqual(order.buyer_type, "guest")
        self.assertEqual(order.contact_name, "Guest")

    def test_import_deduplicates_product_but_not_store_prices(self):
        data = normalize({"code":"12345678", "product_name":"Test oats", "brands":"Brand",
            "nutriments":{"fat_100g":2, "salt_100g":float("nan"), "injected":99}})
        self.assertEqual(data["nutrients"], {"fat_100g":2})
        token = signing.dumps(data, salt="catalog-preview")
        first = add_listing(self.manager, "east", name="ignored", category="ignored", price_cents=350, stock=4, token=token)
        self.manager.is_superuser=True; self.manager.save()
        second = add_listing(self.manager, "west", name="ignored", category="ignored", price_cents=450, stock=7, token=token)
        self.assertEqual(first.product_id, second.product_id)
        self.assertEqual(ProductSource.objects.count(), 1)
        self.assertTrue(verify(first))
        with self.assertRaises(ValidationError):
            add_listing(self.manager, "east", name="x", category="x", price_cents=1, stock=1, token=token+"tampered")
        self.client.force_login(self.manager)
        with patch("catalog.providers.OpenFoodFacts.search", return_value=[data]):
            self.assertContains(self.client.get("/manage/east/import/?query=oats"), "Test oats")

    def test_shared_provider_budget(self):
        for _ in range(8): quota()
        with self.assertRaises(ValidationError): quota()

    def test_warehouse_transfer_atomic_idempotent_and_scoped(self):
        warehouse = Warehouse.objects.create(name="Depot", address="Example")
        stock = WarehouseStock.objects.create(warehouse=warehouse, product=self.product)
        with self.assertRaises(PermissionDenied):
            move(self.manager, stock.pk, 5, uuid.uuid4())
        self.manager.is_superuser=True; self.manager.save()
        move(self.manager, stock.pk, 10, uuid.uuid4())
        key = uuid.uuid4()
        move(self.manager, stock.pk, 4, key, self.item.pk)
        move(self.manager, stock.pk, 4, key, self.item.pk)
        with self.assertRaises(ValidationError):
            move(self.manager, stock.pk, 7, uuid.uuid4(), self.item.pk)
        stock.refresh_from_db(); self.item.refresh_from_db()
        self.assertEqual((stock.quantity, self.item.stock), (6, 9))
        self.assertTrue(verify(self.item))

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    def test_stripe_wait_then_verified_payment(self):
        set_quantity(self.customer, self.east, self.item.pk, 1)
        order = checkout(self.customer, self.east, uuid.uuid4(), provider="stripe")
        with patch("orders.stripe_gateway.validate", return_value={"decision":"waiting", "payment_id":"cs_test_x", "url":"https://checkout.stripe.com/test"}):
            process_one()
        job = PaymentJob.objects.get()
        self.assertEqual(job.provider_session, "cs_test_x")
        self.assertEqual(job.state, "queued")
        self.item.refresh_from_db(); self.assertEqual(self.item.reserved, 1)
        PaymentJob.objects.update(next_attempt=timezone.now())
        with patch("orders.stripe_gateway.validate", return_value={"decision":"approved", "payment_id":"cs_test_x"}):
            process_one()
        order.refresh_from_db(); self.assertEqual(order.status,"confirmed")

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    def test_stripe_adapter_uses_snapshot_and_rejects_wrong_amount(self):
        from orders.stripe_gateway import validate, client
        self.assertIsNotNone(client())
        set_quantity(self.customer, self.east, self.item.pk, 1)
        order = checkout(self.customer, self.east, uuid.uuid4(), provider="stripe")
        api = MagicMock()
        session = SimpleNamespace(id="cs_test_x", livemode=False, client_reference_id=str(order.pk),
            amount_total=399, currency="cad", payment_status="unpaid", status="open", url="https://checkout.stripe.com/test")
        api.v1.checkout.sessions.create.return_value=session
        with patch("orders.stripe_gateway.client", return_value=api):
            self.assertEqual(validate(order.payment_job)["decision"],"waiting")
            args=api.v1.checkout.sessions.create.call_args
            self.assertEqual(args.kwargs["options"]["idempotency_key"],f"checkout:{order.pk}")
            self.assertEqual(args.args[0]["line_items"][0]["price_data"]["unit_amount"],399)
            session.amount_total=1
            with self.assertRaises(PaymentUnavailable): validate(order.payment_job)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret")
    def test_webhook_signature_required_and_duplicates_harmless(self):
        payload=json.dumps({"id":"evt_test", "object":"event", "livemode":False, "type":"checkout.session.completed",
            "data":{"object":{"id":"cs_test_unknown"}}}).encode()
        self.assertEqual(self.client.post("/payments/stripe/webhook/",payload,content_type="application/json").status_code,400)
        stamp=int(time.time())
        signature=hmac.new(b"whsec_test_secret", str(stamp).encode()+b"."+payload,hashlib.sha256).hexdigest()
        for _ in range(2):
            self.assertEqual(self.client.post("/payments/stripe/webhook/",payload,content_type="application/json",
                HTTP_STRIPE_SIGNATURE=f"t={stamp},v1={signature}").status_code,200)
