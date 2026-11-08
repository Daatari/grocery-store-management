#include "../include/department.h"

#include <cstring>
#include <iostream>

#include "../include/product.h"

Department::Department(const char* departmentName) {
    strncpy(this->departmentName, departmentName,
            sizeof(this->departmentName) - 1);
    this->departmentName[sizeof(this->departmentName) - 1] = '\0';
    this->products = new Product[100];
    this->productCount = 0;
}

void Department::displayAllProducts() {
    for (int i = 0; i < this->productCount; i++) {
        std::cout << i + 1 << ". " << this->products[i].getProductName()
                  << " | $" << this->products[i].getProductPrice()
                  << " | Stock: " << this->products[i].getProductQuantity()
                  << "\n";
    }
}
void Department::addProduct(Product& product) {
    if (this->productCount < 100) {
        this->products[this->productCount++] = product;
    } else {
        std::cout << "Department is full. Cannot add more products.\n";
    }
}

int Department::getProductCount() {
    return this->productCount;
}

std::string Department::getDepartmentName() {
    return this->departmentName;
}

Product* Department::getProductList() {
    return this->products;
}

bool Department::reduceProductQuantity(int index, int qty) {
    if (index < 0 || index >= this->productCount || qty <= 0) {
        return false;
    }

    int currentQty = this->products[index].getProductQuantity();

    if (qty > currentQty) {
        return false;
    }

    std::string name = this->products[index].getProductName();
    double price = this->products[index].getProductPrice();

    this->products[index] = Product(name, price, currentQty - qty);
    return true;
}

bool Department::increaseProductQuantity(int index, int qty) {
    if (index < 0 || index >= this->productCount || qty <= 0) {
        return false;
    }

    int currentQty = this->products[index].getProductQuantity();
    std::string name = this->products[index].getProductName();
    double price = this->products[index].getProductPrice();

    this->products[index] = Product(name, price, currentQty + qty);
    return true;
}

int Department::findProductIndexByName(const std::string& productName) {
    for (int i = 0; i < this->productCount; i++) {
        if (this->products[i].getProductName() == productName) {
            return i;
        }
    }

    return -1;
}