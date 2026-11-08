#pragma once
#include <string>

#include "csv.h"

class Menu {
public:
    csv fileManager;
    virtual void start();
    std::string styledInput(std::string input);
    std::string styledError(std::string input);
    std::string styledSuccess(std::string input);
};