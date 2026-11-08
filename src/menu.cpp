#include "../include/menu.h"

#include <iostream>

void Menu::start() {
    std::cout << "Implementation not implemented";
}

std::string Menu::styledInput(std::string input) {
    return "\033[42;97m" + input + "\033[0m";
}

std::string Menu::styledError(std::string input) {
    return "\033[1;31m\n" + input + "\n\033[0m";
}

std::string Menu::styledSuccess(std::string input) {
    return "\033[96m\n" + input + "\n\033[0m";
}
