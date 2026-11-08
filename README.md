# Grocery Store Management

A first-year C++ team project, revisited to explore how a small application changes when several customers and stores share the same data.

The original project used menus and CSV files. This version adds a browser storefront, store management, stock reservations, and payment adapters. The interesting part is what happens when a customer leaves a cart, a payment response arrives late, or two people try to buy the last item.

**C++17 · Python / Django · PostgreSQL · Docker Compose · Stripe test mode**

## Try it

Install Docker with Linux containers and Compose v2, plus Python 3.12. From the repository root:

```sh
python tools/deploy.py up
python tools/deploy.py credentials
```

Open **http://localhost:8080**. The first start creates two stores, an empty warehouse, and sample accounts. Credentials are generated locally in the ignored `deployment/.env` file.

- Shop as a guest or sign in as `customer`. Add items and place a simulated order.
- Use `manager-east` or `manager-harbour` to manage that store or import a reviewed Open Food Facts product.
- Use `admin` to receive warehouse stock, transfer it to a store, and inspect logs from both web servers and the payment worker.

The simulator supports approval, decline, and a delayed response. Optional [Stripe test checkout](docs/payments.md) needs your own test credentials. No real charges are supported.

`python tools/deploy.py down` stops the sandbox while preserving its database volumes.

## What changed

| Problem explored | Implementation |
| --- | --- |
| Shoppers competing for stock | Row-locked reservations, expiry, constraints, and concurrency tests |
| Uncertain payment outcomes | Durable jobs, retry leases, provider idempotency, and protected reservations |
| Multiple stores | Shared products with separate prices and inventory per store |
| Guest and account purchases | Customer identity separate from login credentials; historical order snapshots |
| Replenishment | Warehouse receipts and atomic, audited transfers |
| External catalog data | Reviewed imports, barcode deduplication, bounded input, and source attribution |
| Multiple web instances | Shared PostgreSQL sessions and state; centralized operational logs |

The main application is a **modular monolith**. Inventory and checkout share one transactional database. A separate simulated payment provider makes network failures observable; its C++ rule kernel has a small plugin interface.

[Architecture](docs/architecture.md) · [Database schema](docs/schema.md) · [Operations and tests](docs/operations.md) · [Security](docs/security.md)

## Project history

In the original PRG210 team project, I implemented the shopping cart and connected it to the customer menu, stock updates, and CSV storage. The project was developed with Joseph Ho, Izaac-Rob, and rachelchowww.

The later architecture work is an AI-assisted learning extension, separate from the course submission and my teammates' contributions. The [original implementation](https://github.com/Daatari/grocery-store-management/tree/d0137342df344df64385ab0c7cd9e2b34b89b12f) and [contributor record](CONTRIBUTORS.md) remain available.

## C++ components

The earlier standalone CLI remains alongside the web application. Its file storage is independent of the web database.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --config Debug
ctest --test-dir build -C Debug --output-on-failure
```

CI also tests the web application with SQLite and PostgreSQL, concurrent reservations, and browser/failover checks against the Linux deployment.

## Scope

This is a local learning application. Orders are pickup-only and exclude tax, refunds, delivery, and real payments. Containers demonstrate Linux processes and networks on one Docker host, not independent machines or a highly available deployment. Food metadata is community supplied and must be checked against packaging.
