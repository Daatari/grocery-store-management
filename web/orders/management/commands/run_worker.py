import time
import tempfile
from pathlib import Path
from django.core.management.base import BaseCommand
from orders.worker import process_one, sweep_expired, event


class Command(BaseCommand):
    help = "Process durable payment jobs and expire abandoned cart reservations."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            try:
                sweep_expired()
                processed = process_one()
                (Path(tempfile.gettempdir()) / "grocery-worker.heartbeat").touch()
            except Exception:
                event("worker.error", "ERROR", "worker_cycle_failed")
                if options["once"]:
                    raise
                processed = False
            if options["once"]:
                return
            if not processed:
                time.sleep(1)
