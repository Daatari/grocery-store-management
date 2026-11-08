#pragma once
#include "customerMenu.h"
#include "managerMenu.h"
#include "menu.h"

class MainMenu : public Menu {
private:
    ManagerMenu managerMenu;
    CustomerMenu customerMenu;

public:
    void start() override;
};