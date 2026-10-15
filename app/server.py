"""Synthetic invoice risk service. No real financial data should be submitted."""
import json
import logging
import os
import sqlite3
from pathlib import Path
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from contextlib import contextmanager

LOCK = Lock()
logging.basicConfig(level=logging.INFO, format="%(message)s")

def _connect():
    if os.getenv("DATABASE_URL") or os.getenv("DB_HOST"):
        import psycopg
        if os.getenv("DATABASE_URL"):
            return psycopg.connect(os.environ["DATABASE_URL"])
        return psycopg.connect(host=os.environ["DB_HOST"], dbname="controls", user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], sslmode="require", connect_timeout=5)
    return sqlite3.connect(os.getenv("SQLITE_PATH", "invoices.db"))

@contextmanager
def connect():
    db = _connect()
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS invoices (vendor TEXT NOT NULL, reference TEXT NOT NULL, amount TEXT NOT NULL, PRIMARY KEY(vendor, reference))")

def assess(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    vendor = payload.get("vendor", "")
    reference = payload.get("reference", "")
    if not isinstance(vendor, str) or not isinstance(reference, str):
        raise ValueError("vendor and reference must be strings")
    vendor, reference = vendor.strip().casefold(), reference.strip().casefold()
    if not vendor or not reference or max(len(vendor),len(reference)) > 200:
        raise ValueError("vendor and reference are required; maximum 200 characters")
    try:
        amount = Decimal(str(payload.get("amount", "")))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000") or amount.as_tuple().exponent < -2:
            raise ValueError("amount must be positive, at most 1 billion, with at most 2 decimal places")
    except InvalidOperation:
        raise ValueError("amount must be a decimal number") from None
    placeholder = "%s" if (os.getenv("DATABASE_URL") or os.getenv("DB_HOST")) else "?"
    # The unique key is the concurrency boundary, including across ECS replicas.
    with LOCK, connect() as db:
        cursor = db.execute(f"INSERT INTO invoices VALUES ({placeholder},{placeholder},{placeholder}) ON CONFLICT (vendor, reference) DO NOTHING", (vendor, reference, str(amount)))
        duplicate = cursor.rowcount == 0
    reasons = (["duplicate_reference"] if duplicate else []) + (["high_amount"] if amount >= 10000 else [])
    return {"risk": "review" if reasons else "low", "reasons": reasons, "model_version": "rules-v1"}

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            raw = Path(__file__).with_name("dashboard.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == "/health":
            return self.respond(200, {"status": "alive"})
        if self.path == "/ready":
            try:
                with connect() as db:
                    db.execute("SELECT 1 FROM invoices LIMIT 1")
                return self.respond(200, {"status": "ready"})
            except Exception:
                return self.respond(503, {"status": "unavailable"})
        self.respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/assess":
            return self.respond(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 1 or size > 8192:
                return self.respond(413, {"error": "body must be 1..8192 bytes"})
            payload = json.loads(self.rfile.read(size))
            result = assess(payload)
            self.respond(200, result)
        except (ValueError, UnicodeDecodeError) as exc:
            self.respond(400, {"error": str(exc)})
        except Exception:
            logging.error(json.dumps({"event": "assessment_failed"}))
            self.respond(503, {"error": "temporarily unavailable"})

    def log_message(self, fmt, *args):
        logging.info(json.dumps({"event": "http_request", "status": str(args[1]) if len(args)>1 else "unknown"}))

if __name__ == "__main__":
    initialize()
    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler)
    server.timeout = 10
    server.serve_forever()
