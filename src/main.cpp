#include "store.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>

using namespace grocery;
namespace {
void help() {
    std::cout << "list | cart | add ID QTY | remove ID QTY | cancel | checkout\n"
                 "product ID \"DEPARTMENT\" \"NAME\" PRICE_CENTS STOCK | help | quit\n";
}
void end(std::istringstream& input) {
    input >> std::ws;
    if (!input.eof()) throw ValidationError("Unexpected command arguments.");
}
}
int main(int argc, char** argv) {
    try {
        std::string store = "runtime/store.txt", logs = "runtime/logs", node = "local";
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--help") {
                std::cout << "grocery [--store PATH] [--log-dir PATH] [--node NAME]\n";
                help();
                return 0;
            }
            if (i + 1 >= argc) throw ValidationError("Missing option value.");
            if (arg == "--store") store = argv[++i];
            else if (arg == "--log-dir") logs = argv[++i];
            else if (arg == "--node") node = argv[++i];
            else throw ValidationError("Unknown option.");
        }
        JsonLogger logger(logs, node);
        FileRepository repository(store);
        StoreService service(repository, logger);
        std::cout << "Grocery Store | " << node << "\n";
        help();
        bool failed = false;
        std::string line;
        while (std::getline(std::cin, line)) {
            bool serviceCalled = false;
            try {
                if (line.size() > 4096) throw ValidationError("Command is too long.");
                std::istringstream input(line);
                std::string command;
                if (!(input >> command)) continue;
                if (command == "add" || command == "remove") {
                    int id = 0, count = 0;
                    if (!(input >> id >> count)) throw ValidationError("Expected ID and integer quantity.");
                    end(input);
                    serviceCalled = true;
                    if (command == "add") service.add(id, count); else service.remove(id, count);
                    std::cout << "Saved.\n";
                } else if (command == "product") {
                    Product p{};
                    if (!(input >> p.id >> std::quoted(p.department) >> std::quoted(p.name) >> p.price >> p.stock))
                        throw ValidationError("Expected ID, department, name, price in cents, and stock.");
                    end(input);
                    serviceCalled = true;
                    service.create(p);
                    std::cout << "Product saved.\n";
                } else {
                    end(input);
                    if (command == "quit") break;
                    if (command == "help") help();
                    else if (command == "list") {
                        for (const auto& [id, p] : service.state().products)
                            std::cout << id << " | " << p.department << " | " << p.name << " | "
                                      << money(p.price) << " | stock " << p.stock << '\n';
                    } else if (command == "cart") {
                        for (const auto& [id, count] : service.state().cart)
                            std::cout << id << " | " << service.state().products.at(id).name << " | qty " << count << '\n';
                        std::cout << "Subtotal: " << money(service.total()) << '\n';
                    } else if (command == "cancel") {
                        serviceCalled = true;
                        service.cancel();
                        std::cout << "Cart cancelled; stock restored.\n";
                    }
                    else if (command == "checkout") {
                        serviceCalled = true;
                        const auto amount = service.checkout();
                        std::cout << "Checkout complete: " << money(amount) << " (before tax).\n";
                    } else throw ValidationError("Unknown command. Type help.");
                }
            } catch (const std::exception& error) {
                failed = true;
                // Do not log raw commands or exception text: they may contain user data.
                if (!serviceCalled)
                    logger.emit({"cli.command", "WARN", "rejected", "command_failed", 0});
                std::cerr << "Error: " << error.what() << '\n';
            }
        }
        return failed ? 2 : 0;
    } catch (const std::exception& error) {
        std::cerr << "Startup failed: " << error.what() << '\n';
        return 1;
    }
}
