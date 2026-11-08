import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from tools import logs


def event(**changes):
    value = dict(schema_version=1, event_id="session-1", request_id="session-1",
                 timestamp="2026-11-08T12:00:00Z", node="node-a", service="grocery",
                 operation="cart.add", level="WARN", outcome="rejected",
                 code="validation_failed", duration_us=15)
    value.update(changes)
    return value


class LogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = logs.connect(self.root / "events.sqlite")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def write(self, name, rows):
        path = self.root / name
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_reimport_and_identity_collision(self):
        path = self.write("a.jsonl", [event()])
        self.assertEqual(logs.ingest(self.db, [path])["inserted"], 1)
        self.assertEqual(logs.ingest(self.db, [path])["duplicates"], 1)
        conflict = self.write("conflict.jsonl", [event(level="ERROR")])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(logs.ingest(self.db, [conflict])["rejected"], 1)
        self.assertEqual(logs.query(self.db)[0]["level"], "WARN")

    def test_multiple_nodes_filters_and_bound_parameters(self):
        paths = [self.write("a.jsonl", [event()]),
                 self.write("b.jsonl", [event(node="node-b", level="INFO", outcome="success")])]
        logs.ingest(self.db, paths)
        self.assertEqual(len(logs.query(self.db)), 2)
        self.assertEqual(len(logs.query(self.db, level="WARN", node="node-a", operation="cart.add")), 1)
        self.assertEqual(logs.query(self.db, node="' OR 1=1 --"), [])
        self.assertEqual(logs.query(self.db, since="2027-01-01T00:00:00Z"), [])
        self.assertEqual(len(logs.query(self.db, request_id="session-1")), 2)

    def test_bad_records_do_not_hide_valid_events(self):
        path = self.write("bad.jsonl", [event(), event(schema_version=2), event(duration_us=-1),
                                       event(timestamp="invalid"), event(duration_us=True)])
        with path.open("ab") as out:
            out.write(b"not json\n" + b"x" * 70000 + b"\n" + b'{"partial":')
        with contextlib.redirect_stderr(io.StringIO()):
            result = logs.ingest(self.db, [path])
        self.assertEqual(result, {"inserted": 1, "duplicates": 0, "rejected": 7})
        self.assertEqual(len(logs.query(self.db)), 1)

    def test_partial_line_is_retriable(self):
        path = self.root / "partial.jsonl"
        data = json.dumps(event()).encode()
        path.write_bytes(data[:20])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(logs.ingest(self.db, [path])["rejected"], 1)
        with path.open("ab") as out:
            out.write(data[20:] + b"\n")
        self.assertEqual(logs.ingest(self.db, [path])["inserted"], 1)

    def test_limits_and_reopening(self):
        path = self.write("a.jsonl", [event()])
        logs.ingest(self.db, [path])
        with self.assertRaises(ValueError):
            logs.query(self.db, limit=0)
        with self.assertRaises(ValueError):
            logs.query(self.db, since="2026-99-99T00:00:00Z")
        second = logs.connect(self.root / "events.sqlite")
        try:
            self.assertEqual(len(logs.query(second)), 1)
        finally:
            second.close()


if __name__ == "__main__":
    unittest.main()
