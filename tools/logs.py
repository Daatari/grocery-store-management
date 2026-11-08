"""Collect structured application logs in SQLite and inspect failures. Standard library only."""
import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from pathlib import Path

FIELDS = {"schema_version", "event_id", "request_id", "timestamp", "node", "service",
          "operation", "level", "outcome", "code", "duration_us"}
TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("expected UTC timestamp YYYY-MM-DDTHH:MM:SSZ")
    dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return value


def validate(event):
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise ValueError("unexpected event fields")
    if type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ValueError("unsupported schema version")
    timestamp(event["timestamp"])
    for key in ("event_id", "request_id", "node", "service", "operation", "code"):
        if not isinstance(event[key], str) or not TOKEN.fullmatch(event[key]):
            raise ValueError("invalid event identifier")
    if event["level"] not in ("INFO", "WARN", "ERROR"):
        raise ValueError("invalid severity")
    if event["outcome"] not in ("success", "rejected", "failure"):
        raise ValueError("invalid outcome")
    duration = event["duration_us"]
    if type(duration) is not int or not 0 <= duration <= 2**63 - 1:
        raise ValueError("invalid duration")
    return event


def connect(path):
    database = sqlite3.connect(path, timeout=5)
    database.execute("PRAGMA journal_mode=WAL")
    database.execute("""CREATE TABLE IF NOT EXISTS events (
        node TEXT NOT NULL, event_id TEXT NOT NULL, timestamp TEXT NOT NULL,
        level TEXT NOT NULL, operation TEXT NOT NULL, request_id TEXT NOT NULL,
        payload TEXT NOT NULL, PRIMARY KEY (node, event_id))""")
    database.execute("CREATE INDEX IF NOT EXISTS events_level_time ON events(level, timestamp)")
    database.execute("CREATE INDEX IF NOT EXISTS events_operation_time ON events(operation, timestamp)")
    database.execute("CREATE INDEX IF NOT EXISTS events_time ON events(timestamp)")
    database.commit()
    return database


def ingest(database, paths):
    """One transaction per file; duplicates are safe, conflicting identities are rejected."""
    counts = {"inserted": 0, "duplicates": 0, "rejected": 0}
    for path in paths:
        with Path(path).open("rb") as source, database:
            line_number = 0
            while True:
                raw = source.readline(65537)
                if not raw:
                    break
                line_number += 1
                try:
                    if len(raw) > 65536:
                        while raw and not raw.endswith(b"\n"):
                            raw = source.readline(65537)
                        raise ValueError("event exceeds 64 KiB")
                    # An unterminated final line may still be in flight. Retry after append.
                    if not raw.endswith(b"\n"):
                        raise ValueError("incomplete event line")
                    event = validate(json.loads(raw))
                    payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
                    old = database.execute("SELECT payload FROM events WHERE node=? AND event_id=?",
                                           (event["node"], event["event_id"])).fetchone()
                    if old:
                        if old[0] != payload:
                            raise ValueError("event identity conflicts with stored content")
                        counts["duplicates"] += 1
                        continue
                    database.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                                     (event["node"], event["event_id"], event["timestamp"],
                                      event["level"], event["operation"], event["request_id"], payload))
                    counts["inserted"] += 1
                except (ValueError, UnicodeError, TypeError) as error:
                    counts["rejected"] += 1
                    # Show location and reason, never the raw event payload.
                    print(f"{Path(path).name}:{line_number}: rejected ({error})", file=sys.stderr)
    return counts


def query(database, *, level=None, node=None, operation=None, request_id=None, since=None, limit=50):
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be 1-1000")
    clauses, values = [], []
    for column, value in (("level", level), ("node", node), ("operation", operation), ("request_id", request_id)):
        if value is not None:
            clauses.append(f"{column} = ?")  # Column names are fixed, user values are bound.
            values.append(value)
    if since:
        clauses.append("timestamp >= ?")
        values.append(timestamp(since))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = database.execute("SELECT payload FROM events" + where +
                            " ORDER BY timestamp DESC, node, event_id LIMIT ?", values + [limit])
    return [json.loads(row[0]) for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="runtime/events.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("ingest", help="import completed JSONL events; safe to repeat")
    load.add_argument("paths", nargs="+", type=Path)
    find = commands.add_parser("query", help="print matching events as JSON lines")
    find.add_argument("--level", choices=["INFO", "WARN", "ERROR"])
    for name in ("node", "operation", "request-id", "since"):
        find.add_argument("--" + name)
    find.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    database = None
    try:
        if args.command == "query" and not Path(args.db).is_file():
            raise ValueError("database does not exist; ingest logs first")
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
        database = connect(args.db)
        if args.command == "ingest":
            counts = ingest(database, args.paths)
            print(json.dumps(counts))
            return 2 if counts["rejected"] else 0
        for event in query(database, level=args.level, node=args.node, operation=args.operation,
                           request_id=args.request_id, since=args.since, limit=args.limit):
            print(json.dumps(event))
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Log tool failed: {error}", file=sys.stderr)
        return 1
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    sys.exit(main())
