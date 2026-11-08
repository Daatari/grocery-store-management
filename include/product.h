#pragma once
#include <string>
class Product {
private:
    std::string name;
    double price;
    int quantity;

public:
    Product(std::string name = "", double price = 0.0, int quantity = 0);
    std::string getProductName();
    double getProductPrice();
    int getProductQuantity();
    void show();
};