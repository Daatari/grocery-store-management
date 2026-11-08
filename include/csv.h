#pragma once
#include "../include/cart.h"
#include "../include/department.h"
#include "../include/globals.h"
#include "../include/product.h"

struct csv {
    void loadDataFromCsv(const char* filePath);
    void store_csv();
    void loadCartFromCsv(Cart& cart);
};  // namespace csv