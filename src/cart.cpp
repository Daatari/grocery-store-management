#include "../include/cart.h"

#include <fstream>
#include <iostream>

Cart::Cart(char name, int capacity) {
    this->name = name;
    this->capacity = capacity;
    this->elementsInCart = 0;
    this->isCheckedOut = false;
    this->items = new CartItem[this->capacity];
}

Cart::~Cart() {
    delete[] this->items;
    this->items = nullptr;
}

bool Cart::addItem(Product* addedItem, int qty) {
    if (addedItem == nullptr || qty <= 0) {
        return false;
    }

    for (int i = 0; i < elementsInCart; i++) {
        if (items[i].product.getProductName() == addedItem->getProductName()) {
            items[i].qty += qty;
            return true;
        }
    }

    if (elementsInCart >= capacity) {
        return false;
    }

    items[elementsInCart].product = *addedItem;
    items[elementsInCart].qty = qty;
    elementsInCart++;

    return true;
}

bool Cart::removeItem(int indexChoice, int qty) {
    if (indexChoice < 0 || indexChoice >= elementsInCart || qty <= 0 || qty > items[indexChoice].qty) {
        return false;
    }

    if (qty <= items[indexChoice].qty) {
        for (int i = indexChoice; i < elementsInCart - 1; i++) {
            items[i] = items[i + 1];
        }

        elementsInCart--;
    } else {
        items[indexChoice].qty -= qty;
    }

    return true;
}

void Cart::printItems() const {
    if (elementsInCart == 0) {
        std::cout << "Cart is empty.\n";
        return;
    }

    for (int i = 0; i < elementsInCart; i++) {
        std::cout << "[" << i + 1 << "] " << items[i].product.getProductName()
                  << " | Qty: " << items[i].qty << " | Price: $"
                  << items[i].product.getProductPrice() << '\n';
    }
}

CartItem Cart::getItem(int index) const {
    return items[index];
}

bool Cart::status() const {
    return this->isCheckedOut;
}

void Cart::save() {
    std::ofstream writeFile(cartCsvFile);

    if (!writeFile.is_open()) {
        std::cout << "Error opening cart file\n";
        return;
    }

    writeFile << elementsInCart << '\n';

    for (int i = 0; i < elementsInCart; i++) {
        writeFile << items[i].product.getProductName() << ","
                  << items[i].product.getProductPrice() << "," << items[i].qty
                  << '\n';
    }

    writeFile.close();
    std::cout << "Cart saved\n";
}

void Cart::deleteSave() {
    std::ofstream writeFile("cart.csv");
    if (!writeFile.is_open()) {
        std::cout << "Error opening cart.csv\n";
        return;
    }

    writeFile << 0 << '\n';
    writeFile.close();

    std::cout << "Cart save deleted\n";
}

int Cart::getSize() const {
    return this->elementsInCart;
}

bool Cart::isEmpty() const {
    return elementsInCart == 0;
}