# Grocery Store Management System

A C++17 terminal application for browsing a grocery inventory, managing departments and products, and maintaining a shopping cart backed by CSV files.

A collaborative PRG210 project, presented by Danny Atari. See the contribution summary and team credits below.

## What the project demonstrates

- Separate customer and manager menus, with a shared menu base class.
- Product and department models, dynamically allocated storage, and inventory updates.
- Cart item addition, display, removal, and CSV saving.
- Reading and writing a small structured inventory file.

This is an educational prototype. Checkout and tax calculation are not implemented in the current customer interface. See [known limitations](#known-limitations) before evaluating the demo.

## My contribution — Danny Atari

The original history records my commit `5a5639230d8881c721a294d031743becc1d10dd0`, titled “Initial implementation of cart class.” It introduces the cart class and includes customer-menu integration, cart CSV handling, inventory quantity helpers, and related application wiring. Subsequent team commits also modify this work; the current version is a shared result.

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the full attribution record.

## Build and run

Requirements: a C++17 compiler and GNU Make in a Linux environment. The supplied development-container configuration uses an Ubuntu C++ image. On Windows, use a configured WSL Linux environment or a VS Code development container.

From the repository root:

```sh
cp data/grocery.sample.csv grocery.csv
cp data/cart.sample.csv cart.csv
make
./build/main
```

The Makefile defaults to `clang++`. To use GCC:

```sh
make CXX=g++
./build/main
```

Run from the repository root because the application uses relative CSV paths. To rebuild after changing headers, run `make clean` before `make`; the current Makefile does not track header dependencies.

Verified on Windows with Visual Studio MSVC 14.51 in C++17 mode: compilation and the customer demonstration below passed. The Linux Makefile instructions have been inspected but not executed. Compiler warnings remain for variable shadowing and numeric conversions.

## Try the application

For Windows with Visual Studio installed, open **x64 Native Tools Command Prompt for VS**, change to this repository, and run:

```bat
if not exist build mkdir build
copy data\grocery.sample.csv grocery.csv
copy data\cart.sample.csv cart.csv
cl /nologo /std:c++17 /EHsc /W4 /D_CRT_SECURE_NO_WARNINGS src\*.cpp /Fo:build\ /Fe:build\main.exe
build\main.exe
```

### Customer walkthrough

1. Choose **Customer [1]**, then **Browse Departments [1]** and department **1** to inspect Produce.
2. Choose **Add Item to Cart [2]**, department **1**, product **1**, and quantity **2**.
3. Choose **View Cart [3]** to inspect the cart.
4. Choose **Exit [6]** to return to the main menu, then **Exit [3]**.

Adding an item writes both CSV files and reduces inventory immediately. To reset the demonstration, copy the sample files again. This flow was executed successfully: the cart contained two apples, stock changed from 16 to 14, both CSV files were saved, and the application exited with code 0.

For management features, choose **Manager [2]**: list departments, add a department, add an item, or save changes. Use simple names without spaces or commas for the current parser and input routines.

## Project structure

| Location | Purpose |
| --- | --- |
| `src/`, `include/` | C++ implementations and headers |
| `src/cart.cpp` | Cart storage, item operations, and saving |
| `src/customerMenu.cpp` | Customer browsing and cart interaction |
| `src/managerMenu.cpp` | Department and product management |
| `src/csv.cpp` | Inventory and cart file handling |
| `data/` | Resettable demonstration fixtures |
| `.devcontainer/` | Development-container configuration |

## Known limitations

- Partial removal currently removes the entire cart line while restoring only the requested quantity to inventory.
- A saved cart is loaded into a member object, but entering the customer menu creates a separate customer object. Saved cart restoration therefore does not reach the active customer session.
- Checkout, tax totals, and stock reservation rollback are not implemented.
- Customer and main-menu numeric input do not reliably recover from nonnumeric input or end-of-file.
- Inventory and cart use fixed capacities; department insertion lacks a capacity check. Memory ownership and cleanup need further work.
- CSV parsing assumes valid input and does not handle quoted fields or malformed data robustly.

These are findings from source inspection, not results from a completed runtime test suite. The portfolio packaging leaves the team source files unchanged.

## Attribution and release status

Based on the private team repository `Joelute/PRG210-Final-Project`, snapshot `a1d24d5bcb34bf4753b0ff7f7a651d24ccd236f7`. The private original is not a publicly accessible demo link.

No license was found in the inspected snapshot. No open-source license is granted by this portfolio publication. Danny Atari confirmed contributor approval and course permission for this public portfolio copy on November 8, 2026. The assignment handout and original Git history are excluded from this package.

