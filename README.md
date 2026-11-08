# Grocery Store Management

A first-year C++ team project, revisited as a systems architecture learning exercise.

The original application let customers browse groceries and manage a cart, with a separate manager menu for inventory. This version keeps that domain but reworks how the application manages state, saves changes, and reports failures.

**C++17 · Python · SQLite · CMake · GitHub Actions**

## Why revisit it?

The first version worked around global inventory and separate CSV files. Menu code handled business rules and file writes together, which made bugs difficult to isolate. A cart change could also update inventory without successfully saving the cart.

The refactor applies systems architecture concepts to those specific problems:

- **Separate responsibilities:** the command interface calls a service; storage and logging sit behind small interfaces.
- **Consistent state changes:** inventory and cart reservations are saved together. Failed saves leave the previous state intact.
- **Explicit ownership:** standard containers replace owning pointers, and product IDs replace name-based matching.
- **Useful diagnostics:** structured logs can be collected from multiple app instances and searched in SQLite.
- **Testable failures:** tests exercise failed writes, invalid data, restarts, and repeated log imports.

The [architecture notes](docs/architecture.md) explain the before-and-after decisions and their tradeoffs.

## My contribution

In the original team project, I implemented the cart and integrated it with the customer menu, stock updates, and CSV storage. The project was developed with Joseph Ho, Izaac-Rob, and rachelchowww.

This later refactor is a separate learning extension developed with AI assistance. The [original implementation](https://github.com/Daatari/grocery-store-management/tree/d0137342df344df64385ab0c7cd9e2b34b89b12f) and [team credits](CONTRIBUTORS.md) are preserved.

## Build and test

Requires a C++17 compiler, CMake 3.20+, and Python 3.9+. Python tools use the standard library only.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --config Debug
ctest --test-dir build -C Debug --output-on-failure
```

The executable is `build/grocery` on a typical Linux build, or `build/Debug/grocery.exe` with Visual Studio on Windows.

## Try it

On Linux, from the repository root:

```sh
mkdir -p runtime
cp data/store.sample.txt runtime/store.txt
./build/grocery --store runtime/store.txt --node local
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force runtime
Copy-Item data/store.sample.txt runtime/store.txt
.\build\Debug\grocery.exe --store runtime/store.txt --node local
```

Then enter:

```text
list
add 1 5
remove 1 2
cart
checkout
quit
```

The cart retains three apples after the partial removal. Checkout reports a $11.97 subtotal; stock is deducted only once. Changes are saved after each successful operation. Copying the sample file again resets the store, so only do that when you want to discard your local changes.

## Collect and inspect logs

The demo runs two independent stores, generates successful and rejected operations, and imports their logs into one SQLite index. A second import demonstrates duplicate handling.

```sh
python tools/demo.py --binary build/grocery
```

On Windows, pass `--binary build/Debug/grocery.exe`. The demo prints its output directory. Use the database path it prints to query events:

```sh
python tools/logs.py --db runtime/demo-TIMESTAMP/events.sqlite query --level WARN --operation cart.add
```

See [operations](docs/operations.md) for commands, log filters, and troubleshooting.

## Scope

This is a local, single-writer application with one cart per store. It demonstrates architecture and operational tooling, not a production checkout system. There is no payment processing, tax calculation, authentication, or distributed database. Log collection is a batch tool, and snapshot saves do not guarantee durability through power loss.
