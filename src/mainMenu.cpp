#include "../include/mainMenu.h"

#include <iostream>

#include "../include/customerMenu.h"
#include "../include/managerMenu.h"

void MainMenu::start() {
    csv fileManager;
    fileManager.loadCartFromCsv(customerMenu.cart);

    int choice;
    std::cout << "\033[3;32m=====";
    std::cout << "Welcome to Grocery Store Management System=====\033[0m";
    while (true) {
        std::cout << "\nCustomer [1]\n";
        std::cout << "Manager [2]\n";
        std::cout << "Exit [3]\n";
        std::cout << this->styledInput("Enter your choice [1, 2, 3]: ");
        std::cin >> choice;

        if (choice == 1) {
            CustomerMenu customerMenu;
            customerMenu.start();
        } else if (choice == 2) {
            managerMenu.start();
        } else if (choice == 3) {
            break;
        } else {
            std::cout << this->styledError("Invalid input. Please try again.");
        }
    }
};