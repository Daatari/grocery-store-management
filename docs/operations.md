# Running the lab

`python tools/deploy.py up` generates local credentials, builds the image, starts PostgreSQL, migrates the schema, initializes an empty catalog, and waits for health checks. Docker must use Linux containers. The first build downloads images and dependencies.

The stack contains Nginx, two identical web instances, PostgreSQL, a payment/expiry worker, the simulator, a collector, and a one-shot migration container. Sessions are stored in PostgreSQL. Only Nginx binds to localhost port 8080. Web/worker processes have outbound connectivity for Stripe and Open Food Facts. These are isolated processes/networks on one Docker host, not independent machines.

Application containers run as a non-root user with read-only root filesystems, temporary `/tmp`, and dedicated writable volumes.

```sh
python tools/deploy.py status
python tools/deploy.py logs
python tools/deploy.py credentials
python tools/deploy.py down
```

Stopping preserves volumes. Changing `.env` does not rotate existing database or user passwords. Back up the database and signing key together; old ledger signatures depend on that key. Backup/restore and key rotation are not automated here.

## Administrator workflows

**System logs** filters events by node, severity, operation, UTC time, or request ID. Application events omit request bodies, query strings, credentials, contact details, and card data. Collection polls every five seconds; files rotate at 10 MiB with three backups per node. Indexed records older than seven days are deleted. Disk reclamation and offset-aware shipping remain future work. Logs are best effort; inventory audit records commit transactionally.

Payments requiring review appear below the log table. Retrying keeps the order and provider key. There is no "assume unpaid" action that could release stock after an unknown payment outcome.

**Warehouse** receives stock or transfers it to a matching store product. Create new warehouse/product stock rows with zero quantity through Django admin, then use audited movements. Transfers represent completed movement, not goods in transit.

Managers can add products manually or review food-catalog results. Search uses a shared eight-request budget per one-minute window and a five-second timeout. Preview tokens expire after 15 minutes. Other applications on the same IP may consume the provider's limits too.

Imported data retains [Open Food Facts](https://world.openfoodfacts.org) product links, barcode, import time, and ODbL attribution. Check its [reuse conditions](https://support.openfoodfacts.org/help/en-gb/12-api-data-reuse/94-are-there-conditions-to-use-the-api) before distributing an imported database. This repository includes no downloaded food dataset or images. Always check packaging; missing allergen data does not establish absence.

## Tests

```sh
python -m venv .venv
# Activate the environment for your shell.
python -m pip install -r web/requirements.txt
cd web
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test tests -v 2
```

For PostgreSQL, install `requirements-postgres.txt` and set `GROCERY_DB_ENGINE=postgres`, `PGHOST`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD`. CI creates a fresh PostgreSQL service and runs the concurrent last-item reservation test.

Root CMake tests cover the C++ CLI and rule kernel. `tests/stack_check.py` uses Playwright against the Compose deployment to exercise checkout, store scope, shared sessions, centralized logs, mobile layout, and web-node failover. CI saves screenshots in the `web-previews` artifact.

Verify the store ledger:

```sh
docker compose --env-file deployment/.env -f deployment/compose.yaml exec web-a python manage.py verify_ledger
```

The older C++ CLI remains independent: copy `data/store.sample.txt` to a runtime path, then run `grocery --store PATH --node local`. `tools/demo.py --binary PATH_TO_GROCERY` exercises two independent files and log collection. It is not a second client for PostgreSQL.
