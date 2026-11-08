#include "../include/managerMenu.h"

#include <iostream>

#include "../include/csv.h"
#include "../include/department.h"
#include "../include/globals.h"

double checkValidation(std::string text) {
    std::cout << text;
    double num;
    while (!(std::cin >> num) || num < 0) {
            std::cout << "\033[1;31m\nInvalid input. Please enter again.\n\033[0m" << text;
            std::cin.clear();
            std::cin.ignore(10000, '\n');
    }
    return num;
}

void displayAllDepartments() {
    std::cout << "There are total " << TotalDepartments << " departments: \n";
    for (int i = 0; i < TotalDepartments; i++) {
        std::cout << i + 1 << ". " << StoreDepartments[i].getDepartmentName()
                  << "\n";
    }
}

void addNewDepartment() {
    char departmentName[100];
    std::cout << "Enter Department Name: ";
    std::cin >> departmentName;
    Department newDepartment(departmentName);
    StoreDepartments[TotalDepartments] = newDepartment;
    TotalDepartments++;
    std::cout << "\033[96mNew department added successfully.\n\033[0m";
}

void addProductToDepartment() {
    int departmentIndex;
    displayAllDepartments();

    while (true) {
        departmentIndex = checkValidation("\nEnter department number [0 to go back]:");
        if (departmentIndex > TotalDepartments) {
            std::cout << "\033[1;31m\nDepartment not exist.\n\033[0m";
            continue;
        } else if (departmentIndex == 0) {
            break;
        }

        StoreDepartments[departmentIndex - 1].displayAllProducts();

        std::string itemName;
        double itemPrice;
        int itemQuantity;
        // TODO(finished): Validate each input. If invalid, print the same prompt again.
        std::cout << "Enter new item name: ";
        std::cin >> itemName;
        itemPrice = checkValidation("Enter item price: ");
        itemQuantity = checkValidation("Enter item quantity: ");
        Product newProduct(itemName, itemPrice, itemQuantity);

        StoreDepartments[departmentIndex - 1].addProduct(newProduct);
        std::cout << "\033[96mItem added successfully.\n\033[0m";
        break;
    }
}

void ManagerMenu::start() {
    int choice;
    while (true) {
        std::cout << "\nList Departments [1]\n";
        std::cout << "Add Department [2]\n";
        std::cout << "Add Item to Department [3]\n";
        std::cout << "Save Changes to CSV [4]\n";
        std::cout << "Exit [5]\n";
        choice = checkValidation(this->styledInput("Enter your choice [1, 2, 3, 4, 5]: "));

        if (choice == 1) {
            displayAllDepartments();
        } else if (choice == 2) {
            addNewDepartment();
        } else if (choice == 3) {
            addProductToDepartment();
        } else if (choice == 4) {
            fileManager.store_csv();
        } else if (choice == 5) {
            break;
        } else {
            choice = checkValidation(this->styledError("Invalid input. Please try again."));
        }
    }
};