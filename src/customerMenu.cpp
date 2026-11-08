#include "../include/customerMenu.h"

#include "../include/csv.h"
#include "../include/globals.h"

CustomerMenu::CustomerMenu() : cart('A', 100) {
}

void CustomerMenu::displayCustomerDepartments() {
    for (int i = 0; i < TotalDepartments; i++) {
        std::cout << i + 1 << ". " << StoreDepartments[i].getDepartmentName()
                  << "\n";
    }
}

void CustomerMenu::browseDepartmentProducts() {
    int departmentIndex;
    displayCustomerDepartments();

    while (true) {
        std::cout << "Enter department number [0 to go back]: ";
        std::cin >> departmentIndex;

        if (departmentIndex == 0) {
            break;
        } else if (departmentIndex < 1 || departmentIndex > TotalDepartments) {
            std::cout << this->styledError("Invalid department.\n");
            continue;
        }

        StoreDepartments[departmentIndex - 1].displayAllProducts();
        break;
    }
}

void CustomerMenu::addProductToCart(CustomerMenu& menu) {
    int departmentIndex;
    displayCustomerDepartments();

    while (true) {
        std::cout << "Enter department number [0 to go back]: ";
        std::cin >> departmentIndex;

        if (departmentIndex == 0) {
            return;
        } else if (departmentIndex < 1 || departmentIndex > TotalDepartments) {
            std::cout << this->styledError("Invalid department.\n");
            continue;
        }

        Department& dept = StoreDepartments[departmentIndex - 1];
        dept.displayAllProducts();

        int productIndex;
        std::cout << "Enter product number [0 to go back]: ";
        std::cin >> productIndex;

        if (productIndex == 0) {
            return;
        } else if (productIndex < 1 || productIndex > dept.getProductCount()) {
            std::cout << this->styledError("Invalid product.\n");
            return;
        }

        int qty;
        std::cout << "Enter quantity: ";
        std::cin >> qty;

        if (qty <= 0) {
            std::cout << this->styledError("Invalid quantity.\n");
            return;
        }

        Product* products = dept.getProductList();
        int realIndex = productIndex - 1;

        if (products[realIndex].getProductQuantity() < qty) {
            std::cout << this->styledError("Not enough stock available.\n");
            return;
        }

        if (menu.cart.addItem(&products[realIndex], qty)) {
            dept.reduceProductQuantity(realIndex, qty);
            menu.cart.save();
            fileManager.store_csv();
            std::cout << "Item added successfully.\n";
        } else {
            std::cout << this->styledError("Could not add item to cart.\n");
        }

        return;
    }
}

void CustomerMenu::removeProductFromCart(CustomerMenu& menu) {
    if (menu.cart.isEmpty()) {
        std::cout << this->styledError("Cart is empty.\n");
        return;
    }

    menu.cart.printItems();

    int cartIndex;
    std::cout << "Enter cart item number [0 to go back]: ";
    std::cin >> cartIndex;

    if (cartIndex == 0) {
        return;
    } else if (cartIndex < 1 || cartIndex > menu.cart.getSize()) {
        std::cout << this->styledError("Invalid cart item.\n");
        return;
    }

    int qty;
    std::cout << "Enter quantity to remove: ";
    std::cin >> qty;

    if (qty <= 0) {
        std::cout << this->styledError("Invalid quantity.\n");
        return;
    }

    CartItem selectedItem = menu.cart.getItem(cartIndex - 1);

    for (int i = 0; i < TotalDepartments; i++) {
        int deptProductIndex = StoreDepartments[i].findProductIndexByName(
            selectedItem.product.getProductName());

        if (deptProductIndex != -1) {
            if (menu.cart.removeItem(cartIndex - 1, qty)) {
                StoreDepartments[i].increaseProductQuantity(deptProductIndex,
                                                            qty);
                menu.cart.save();
                fileManager.store_csv();
                std::cout << "Item removed successfully.\n";
            } else {
                std::cout << this->styledError("Could not remove item.\n");
            }

            return;
        }
    }

    std::cout << "Matching product not found in store.\n";
}

void CustomerMenu::start() {
    int choice;

    while (true) {
        std::cout << "\nBrowse Departments [1]\n";
        std::cout << "Add Item to Cart [2]\n";
        std::cout << "View Cart [3]\n";
        std::cout << "Remove Item from Cart [4]\n";
        std::cout << "Save Cart [5]\n";
        std::cout << "Exit [6]\n";
        std::cout << this->styledInput(
            "Enter your choice [1, 2, 3, 4, 5, 6]: ");
        std::cin >> choice;

        if (choice == 1) {
            browseDepartmentProducts();
        } else if (choice == 2) {
            addProductToCart(*this);
        } else if (choice == 3) {
            cart.printItems();
        } else if (choice == 4) {
            removeProductFromCart(*this);
        } else if (choice == 5) {
            cart.save();
            std::cout << "Cart saved.\n";
        } else if (choice == 6) {
            break;
        } else {
            std::cout << this->styledError("Invalid input. Please try again.");
        }
    }
}