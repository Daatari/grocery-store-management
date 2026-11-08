#pragma once
#include "cart.h"
#include "csv.h"
#include "department.h"
#include "menu.h"

class CustomerMenu : public Menu {
public:
    Cart cart;
    CustomerMenu();
    void start();
    void displayCustomerDepartments();
    void browseDepartmentProducts();
    void addProductToCart(CustomerMenu& menu);
    void removeProductFromCart(CustomerMenu& menu);
};