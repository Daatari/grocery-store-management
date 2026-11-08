"""Exercise the built binary, persisted state, and central log collection together."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import logs


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        def run(node, commands):
            return subprocess.run([executable, "--store", str(root / f"{node}.txt"),
                                   "--log-dir", str(root / "logs"), "--node", node],
                                  input=commands, text=True, capture_output=True, timeout=10)
        for node in ("node-a", "node-b"):
            shutil.copyfile("data/store.sample.txt", root / f"{node}.txt")
        first = run("node-a", "add 1 5\nremove 1 2\ncart\nquit\n")
        assert first.returncode == 0, first.stderr
        assert "qty 3" in first.stdout and "$11.97" in first.stdout
        restarted = run("node-a", "cart\ncheckout\nlist\nquit\n")
        assert restarted.returncode == 0, restarted.stderr
        assert "qty 3" in restarted.stdout and "stock 13" in restarted.stdout
        invalid = run("node-b", "add 1 999\nadd x 2\nadd 1 1\ncart\nquit\n")
        assert invalid.returncode == 2
        assert "qty 1" in invalid.stdout, "CLI must recover after invalid input"
        eof = run("node-b", "cart\n")
        assert eof.returncode == 0 and "qty 1" in eof.stdout
        database = logs.connect(root / "events.sqlite")
        try:
            files = list((root / "logs").glob("*.jsonl"))
            imported = logs.ingest(database, files)
            assert imported["inserted"] > 0 and imported["rejected"] == 0
            assert logs.ingest(database, files)["inserted"] == 0
            warnings = logs.query(database, node="node-b", level="WARN", operation="cart.add")
            assert len(warnings) == 1 and warnings[0]["code"] == "validation_failed"
            assert len({row["node"] for row in logs.query(database)}) == 2
            print(json.dumps({"application": "passed", "log_import": imported}))
        finally:
            database.close()


if __name__ == "__main__":
    main()
