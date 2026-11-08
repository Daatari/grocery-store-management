"""Run two isolated stores and collect their logs. Uses only generated demo data."""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from logs import connect, ingest, query


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    project = Path(__file__).resolve().parents[1]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = project / "runtime" / ("demo-" + stamp)
    root.mkdir(parents=True)
    for node, commands, expected in (
        ("node-a", "add 1 5\nremove 1 2\ncart\ncheckout\nquit\n", 0),
        ("node-b", "add 1 999\nadd 2 1\ncart\nquit\n", 2),
    ):
        state = root / (node + ".txt")
        shutil.copyfile(project / "data/store.sample.txt", state)
        result = subprocess.run([str(binary), "--store", str(state), "--node", node,
                                 "--log-dir", str(root / "logs")], input=commands,
                                text=True, capture_output=True, timeout=15)
        print(f"--- {node} ---\n{result.stdout}", end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != expected:
            raise RuntimeError(f"Unexpected exit status from {node}: {result.returncode}")
    database = connect(root / "events.sqlite")
    try:
        files = sorted((root / "logs").glob("*.jsonl"))
        print("First import:", json.dumps(ingest(database, files)))
        print("Repeated import:", json.dumps(ingest(database, files)))
        print("Rejected cart additions:")
        for event in query(database, level="WARN", operation="cart.add"):
            print(json.dumps(event))
    finally:
        database.close()
    print(f"Demo files: {root}")


if __name__ == "__main__":
    main()
