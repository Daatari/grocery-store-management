# Grocery Store Management System

A C++ console application with separate customer and manager menus. Customers can browse products and manage a shopping cart; managers can add departments and products, update inventory, and save changes to CSV.

Built as a team project for PRG210 using **C++17, object-oriented programming, dynamic memory allocation, and file I/O**.

## My contribution

I implemented the shopping cart and connected it to the customer menu, inventory updates, and CSV storage. My work included:

- Adding products to the cart and tracking quantities.
- Displaying cart contents and saving them to a file.
- Integrating cart actions with stock adjustments.
- Adding cart-loading support and wiring it into the application.

The project was developed with Joseph Ho, Izaac-Rob, and rachelchowww. See [Contributors](CONTRIBUTORS.md) for attribution and the original project history reference.

## How it works

`Product` stores an item's name, price, and stock quantity. `Department` groups products, while `Cart` holds the customer's selections. Customer and manager menus share a common `Menu` base class. Inventory and cart data are stored in local CSV files.

The sample inventory includes Produce, Dairy, and Bakery departments. Adding a product to the cart reduces its available stock and saves the updated inventory.

## Run locally

Run commands from the repository root. Copy the sample files again whenever you want to reset the demo.

### Linux / WSL

Requires a C++17 compiler and GNU Make. The Makefile uses Clang by default; use `make CXX=g++` for GCC.

```sh
cp data/grocery.sample.csv grocery.csv
cp data/cart.sample.csv cart.csv
make
./build/main
```

After changing header files, run `make clean` before rebuilding.

### Windows / Visual Studio

Open **x64 Native Tools Command Prompt for VS** in the repository folder:

```bat
if not exist build mkdir build
copy data\grocery.sample.csv grocery.csv
copy data\cart.sample.csv cart.csv
cl /nologo /std:c++17 /EHsc /W4 /D_CRT_SECURE_NO_WARNINGS src\*.cpp /Fo:build\ /Fe:build\main.exe
build\main.exe
```

### Quick demo

1. Select **Customer**, then **Browse Departments**, and choose **Produce**.
2. Select **Add Item to Cart**, choose **Apples**, and enter a quantity of **2**.
3. Select **View Cart** to see the items, then exit.

The Windows build and this demo have been tested with MSVC 14.51. Linux build instructions have not been tested.

## Current limitations

This version preserves the original coursework implementation. Checkout and tax calculation are not implemented. Known issues include partial cart removal and restoring a saved cart into the active customer session. Input validation, CSV error handling, capacity checks, and memory cleanup also need improvement.

## Source layout

- `src/` — application implementation
- `include/` — class declarations
- `data/` — sample inventory and empty cart
- `.devcontainer/` — C++ development environment
