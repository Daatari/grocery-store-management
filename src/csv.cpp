#include "../include/csv.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "../include/csv.h"

void csv::loadCartFromCsv(Cart& cart) {
    std::ifstream readOnlyFile(cartCsvFile);

    if (!readOnlyFile.is_open()) {
        std::cerr << "Cart file not found\n";
        return;
    }

    std::string line;
    std::getline(readOnlyFile, line);

    if (line.empty()) {
        return;
    }

    int cartItemCount = std::stoi(line);

    for (int i = 0; i < cartItemCount; i++) {
        std::getline(readOnlyFile, line);

        std::string productName;
        double productPrice;
        int cartQty;

        std::stringstream ss(line);
        std::getline(ss, productName, ',');
        ss >> productPrice;
        ss.ignore();
        ss >> cartQty;

        Product newProduct(productName, productPrice, 0);
        cart.addItem(&newProduct, cartQty);
    }
}

void csv::loadDataFromCsv(const char* filePath) {
    std::ifstream readOnlyFile(filePath);
    if (!readOnlyFile.is_open()) {
        std::cerr << "Error opening file" << "\n";
        return;
    }
    std::string line;
    std::getline(readOnlyFile, line);
    TotalDepartments = std::stoi(line);

    for (int index = 0; index < TotalDepartments; index++) {
        std::getline(readOnlyFile, line);
        std::string departmentName;
        int productCount;

        std::stringstream ss(line);
        std::getline(ss, departmentName, ',');
        ss >> productCount;

        Department newDepartment(departmentName.c_str());

        for (int i = 0; i < productCount; i++) {
            std::getline(readOnlyFile, line);
            std::string productName;
            float productPrice;
            int productQuantity;

            std::stringstream ss(line);
            std::getline(ss, productName, ',');
            ss >> productPrice;
            ss.ignore();
            ss >> productQuantity;

            Product newProduct(productName.c_str(), productPrice,
                               productQuantity);
            newDepartment.addProduct(newProduct);
        }
        StoreDepartments[index] = newDepartment;
    }
}

void csv::store_csv() {
    std::ofstream writeFile(groceryCsvFile);
    if (!writeFile.is_open()) {
        std::cerr << "Error opening file for writing\n";
        return;
    }

    writeFile << TotalDepartments << std::endl;

    for (int i = 0; i < TotalDepartments; i++) {
        writeFile << StoreDepartments[i].getDepartmentName() << ","
                  << StoreDepartments[i].getProductCount() << std::endl;

        Product* productArray = StoreDepartments[i].getProductList();

        for (int j = 0; j < StoreDepartments[i].getProductCount(); j++) {
            writeFile << productArray[j].getProductName() << ","
                      << productArray[j].getProductPrice() << ","
                      << productArray[j].getProductQuantity() << std::endl;
        }
    }

    writeFile.close();
    std::cout << "Changes saved successfully.\n";
}