"""Poll rotating JSONL files and maintain a central SQLite index with time-based retention."""
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from logs import connect, ingest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval < 1 or not 1 <= args.retention_days <= 365:
        parser.error("interval must be >=1 and retention-days must be 1-365")
    args.db.parent.mkdir(parents=True, exist_ok=True)
    database = connect(args.db)
    try:
        while True:
            counts = {"inserted": 0, "duplicates": 0, "rejected": 0}
            for path in sorted(args.directory.glob("*.jsonl*")):
                try:
                    result = ingest(database, [path])
                    for key in counts:
                        counts[key] += result[key]
                except FileNotFoundError:
                    continue
            cutoff = (datetime.now(timezone.utc) - timedelta(days=args.retention_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            with database:
                database.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            database.execute("PRAGMA wal_checkpoint(PASSIVE)")
            args.db.with_suffix(".heartbeat").touch()
            if counts["inserted"] or counts["rejected"]:
                print(json.dumps(counts), flush=True)
            if args.once:
                break
            time.sleep(args.interval)
    finally:
        database.close()


if __name__ == "__main__":
    main()
