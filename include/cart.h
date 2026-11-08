#pragma once
#include <iostream>

#include "../include/globals.h"
#include "../include/product.h"

struct CartItem {
    Product product;
    int qty = 0;
};

class Cart {
private:
    char name;
    int capacity;
    int elementsInCart;
    CartItem* items;
    bool isCheckedOut;

public:
    Cart(char name, int capacity);
    ~Cart();

    bool addItem(Product* addedItem, int qty);
    bool removeItem(int indexChoice, int qty);

    void printItems() const;
    CartItem getItem(int index) const;

    bool status() const;
    void save();
    void deleteSave();

    int getSize() const;
    bool isEmpty() const;
};