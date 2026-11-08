"""Internal payment simulator. No card details, external payment network, or real charges."""
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKEN = os.environ.get("GROCERY_PAYMENT_TOKEN", "")
DATABASE = Path(os.environ.get("PAYMENT_DATABASE", "/payment-state/payments.sqlite"))
KERNEL = os.environ.get("PAYMENT_KERNEL", "/usr/local/bin/payment_kernel")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No raw requests or signing headers in access logs.

    def respond(self, status, value):
        body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Signature", hmac.new(TOKEN.encode(), body, hashlib.sha256).hexdigest())
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.respond(200 if self.path == "/health" else 404, {"status": "ok"})

    def do_POST(self):
        if self.path != "/validate":
            return self.respond(404, {"error": "not_found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2048:
                return self.respond(400, {"error": "invalid_length"})
            body = self.rfile.read(size)
            expected = hmac.new(TOKEN.encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, self.headers.get("X-Signature", "")):
                return self.respond(403, {"error": "invalid_signature"})
            value = json.loads(body)
            if set(value) != {"key", "amount_cents", "scenario"}:
                raise ValueError
            key = str(uuid.UUID(value["key"]))
            amount, scenario = value["amount_cents"], value["scenario"]
            if type(amount) is not int or not 0 <= amount <= 1000000000 or scenario not in ("approve", "decline", "timeout"):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            return self.respond(400, {"error": "invalid_request"})
        database = sqlite3.connect(DATABASE, timeout=10)
        first = False
        try:
            with database:
                database.execute("BEGIN IMMEDIATE")
                old = database.execute("SELECT amount, scenario, response FROM payments WHERE key=?", (key,)).fetchone()
                if old:
                    if old[0] != amount or old[1] != scenario:
                        return self.respond(409, {"error": "idempotency_conflict"})
                    response = json.loads(old[2])
                else:
                    result = subprocess.run([KERNEL, str(amount), scenario], capture_output=True, text=True, timeout=3, check=True)
                    response = json.loads(result.stdout)
                    response.update({"key": key, "amount_cents": amount, "payment_id": str(uuid.uuid4())})
                    database.execute("INSERT INTO payments VALUES (?,?,?,?)", (key, amount, scenario, json.dumps(response)))
                    first = True
        except Exception:
            return self.respond(503, {"error": "validator_unavailable"})
        finally:
            database.close()
        if first and scenario == "timeout":
            time.sleep(3)  # Decision committed, response lost: retry returns the same payment_id immediately.
        self.respond(200, response)


def main():
    if len(TOKEN) < 32:
        raise RuntimeError("GROCERY_PAYMENT_TOKEN must be at least 32 characters")
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as database:
        database.execute("CREATE TABLE IF NOT EXISTS payments (key TEXT PRIMARY KEY, amount INTEGER NOT NULL, scenario TEXT NOT NULL, response TEXT NOT NULL)")
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PAYMENT_PORT", "9000"))), Handler).serve_forever()


if __name__ == "__main__":
    main()
