#include "payment_kernel.hpp"
#include <iostream>

int main(int argc, char** argv) {
    try {
        if (argc != 3) return 2;
        std::size_t consumed = 0;
        const auto amount = std::stoll(argv[1], &consumed);
        if (consumed != std::string(argv[1]).size()) return 2;
        payment::Kernel kernel;
        kernel.install(std::make_unique<payment::AmountRule>());
        kernel.install(std::make_unique<payment::SimulationRule>());
        const auto decision = kernel.evaluate({amount, argv[2]});
        std::cout << "{\"decision\":\"" << (decision.approved ? "approved" : "declined")
                  << "\",\"code\":\"" << decision.code << "\"}\n";
        return 0;
    } catch (const std::exception&) { return 2; }
}
