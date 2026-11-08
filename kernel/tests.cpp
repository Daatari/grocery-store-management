#include "payment_kernel.hpp"
#include <stdexcept>

void check(bool value) { if (!value) throw std::runtime_error("Kernel assertion failed"); }
class AlwaysReject : public payment::Rule {
public:
    payment::Decision evaluate(const payment::Request&) const override { return {false, "custom_rule"}; }
};
int main() {
    payment::Kernel kernel;
    check(!kernel.evaluate({100, "approve"}).approved);
    kernel.install(std::make_unique<payment::AmountRule>());
    kernel.install(std::make_unique<payment::SimulationRule>());
    check(kernel.evaluate({798, "approve"}).approved);
    check(!kernel.evaluate({798, "decline"}).approved);
    check(kernel.evaluate({798, "timeout"}).approved);
    check(!kernel.evaluate({-1, "approve"}).approved);
    check(!kernel.evaluate({1000000001, "approve"}).approved);
    check(!kernel.evaluate({1, "unknown"}).approved);
    kernel.install(std::make_unique<AlwaysReject>());
    check(kernel.evaluate({100, "approve"}).code == "custom_rule");
}
