# Running and troubleshooting

## Start with sample data

Copy `data/store.sample.txt` to a new path, such as `runtime/store.txt`, and run the application with `--store runtime/store.txt`. A missing store starts empty; an invalid existing store causes startup to fail rather than silently discarding data.

The current snapshot format begins with `GROCERY 1`, contains product (`P`) and cart (`C`) records, and ends with `END`. Prices are integer cents. Product IDs must be unique, positive integers. Counts, prices, names, file size, and references are checked before the snapshot is accepted. Legacy CSV files are not migrated automatically; preserve them separately if you have data beyond the sample fixtures.

## Commands

```text
list
product 5 "Frozen Food" "Green peas" 299 20
add 5 3
remove 5 1
cart
cancel
add 5 2
checkout
quit
```

`product` creates a product and assigns its department label; duplicate IDs are rejected. `cancel` empties the cart and returns its reservations to stock. `checkout` clears the cart and reports the subtotal before tax. There is no payment integration. EOF exits cleanly. Invalid commands are reported and the following command can still run.

Exit codes: **0** for a clean session, **2** if any command failed, **1** for startup failure. The nonzero command result remains even if later commands succeed, so scripts can detect partial failure.

## Search collected logs

```sh
python tools/logs.py --db runtime/events.sqlite ingest runtime/logs/node-a-SESSION.jsonl runtime/logs/node-b-SESSION.jsonl
python tools/logs.py --db runtime/events.sqlite query --level WARN --operation cart.add
python tools/logs.py --db runtime/events.sqlite query --node node-a --since 2026-11-08T00:00:00Z --limit 20
```

Use actual filenames printed by the demo or found in the log directory. Importing the same files again does not duplicate records. The tool prints inserted, duplicate, and rejected counts. Exit **2** means some lines were rejected while valid events were imported; exit **1** means an I/O, argument, or database failure. Diagnostics include the file and line number without echoing raw payloads. Incomplete final lines can be retried after the producer finishes writing them.

## Common failures

| Symptom | Action |
| --- | --- |
| `validation_failed` on `cart.add` | Check the requested quantity and available stock. No change was committed. |
| `storage_or_internal_error` | Inspect stderr, destination directory permissions, and available disk space. The prior state is retained on a reported save failure. |
| `Store is locked` | Check for a running process using that exact store. Only after confirming none exists, remove that store's empty `.lock` directory. Never remove a live process's lock. |
| Invalid snapshot on startup | Keep a copy for investigation. Restore a known-good backup or copy the sample to a new path; do not overwrite the original blindly. |
| Event identity conflict | Compare the source files. An event identity was reused with different content; the existing record was preserved. |
| Log-write warning after a command | Inspect the log directory and disk space. Do not repeat the business command just because its log failed; the state may already be saved. |

Stop the application before copying a snapshot as a backup. The store is a local, single-writer prototype; do not share its directory over a network or use hard-linked aliases to bypass the lock. Logs and the SQLite index have no automatic retention policy and should be kept in the ignored `runtime/` directory.

## Verification

`ctest` runs business-rule and storage tests, Python log-collector tests, and an end-to-end application test. Tests cover partial removal, insufficient stock, duplicate product IDs, save failure rollback, restart recovery, checkout, cancellation, malformed snapshots, writer exclusion, duplicate imports, conflicting log identities, invalid events, and filters. The application test runs two isolated stores and imports their real generated logs.
