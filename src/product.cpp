#include "../include/product.h"

#include <iostream>

Product::Product(std::string name, double price, int quantity) {
    this->name = name;
    this->price = price;
    this->quantity = quantity;
};

std::string Product::getProductName() {
    return this->name;
}
double Product::getProductPrice() {
    return this->price;
}
int Product::getProductQuantity() {
    return this->quantity;
}
void Product::show() {
    std::cout << name;
    std::cout << price;
    std::cout << quantity;
};
