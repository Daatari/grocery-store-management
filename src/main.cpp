#include "../include/csv.h"
#include "../include/department.h"
#include "../include/globals.h"
#include "../include/mainMenu.h"

Department* StoreDepartments = new Department[100];
int TotalDepartments = 0;
const char* groceryCsvFile = "grocery.csv";
const char* cartCsvFile = "cart.csv";

int main() {
    csv fileManager;
    fileManager.loadDataFromCsv(groceryCsvFile);
    MainMenu menu;
    menu.start();
}