import json
import sqlite3
import tempfile
from pathlib import Path
from django.contrib.auth.models import User
from django.test import TestCase, override_settings


class OperationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="Test-admin-password-73!")
        self.customer = User.objects.create_user("shopper", password="Test-customer-password-73!")

    def test_log_access_requires_superuser_not_just_staff(self):
        self.assertEqual(self.client.get("/operations/logs/").status_code, 302)
        self.customer.is_staff = True
        self.customer.save()
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/operations/logs/").status_code, 403)

    def test_admin_filters_and_missing_index(self):
        self.client.force_login(self.admin)
        with tempfile.TemporaryDirectory() as root:
            index = Path(root) / "events.sqlite"
            with override_settings(LOG_INDEX_PATH=index):
                self.assertContains(self.client.get("/operations/logs/"), "not available yet", status_code=400)
                db = sqlite3.connect(index)
                db.execute("CREATE TABLE events (node TEXT, event_id TEXT, timestamp TEXT, level TEXT, operation TEXT, request_id TEXT, payload TEXT)")
                event = {"node": "web-a", "event_id": "one", "request_id": "one", "timestamp": "2026-11-08T12:00:00Z",
                         "level": "WARN", "operation": "checkout", "code": "http_409", "duration_us": 100}
                db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?)", ("web-a", "one", event["timestamp"], "WARN", "checkout", "one", json.dumps(event)))
                db.commit()
                db.close()
                response = self.client.get("/operations/logs/?node=web-a&level=WARN")
                self.assertContains(response, "http_409")
                self.assertContains(response, "1 matching events")
                self.assertContains(self.client.get("/operations/logs/?node=not-a-node"), "0 matching events")
                self.assertEqual(self.client.get("/operations/logs/?since=invalid").status_code, 400)

    def test_health_and_safe_log_envelope(self):
        with self.assertLogs("grocery.events", level="INFO") as captured:
            response = self.client.get("/health/?private=do-not-record-this")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Server-Node", response)
        self.assertNotIn("do-not-record-this", "".join(captured.output))
