#pragma once
#include "product.h"

class Department {
private:
    char departmentName[100];
    Product *products;
    int productCount;

public:
    Department(const char *departmentName = "");
    void displayAllProducts();
    void addProduct(Product &product);
    std::string getDepartmentName();
    int getProductCount();
    Product *getProductList();
    bool reduceProductQuantity(int index, int qty);
    bool increaseProductQuantity(int index, int qty);
    int findProductIndexByName(const std::string &productName);
};