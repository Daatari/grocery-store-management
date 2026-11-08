#include "payment_kernel.hpp"
#include <stdexcept>
#include <utility>

namespace payment {
void Kernel::install(std::unique_ptr<Rule> rule) {
    if (!rule) throw std::invalid_argument("Rule cannot be null");
    rules_.push_back(std::move(rule));
}
Decision Kernel::evaluate(const Request& request) const {
    if (rules_.empty()) return {false, "no_rules_installed"};
    for (const auto& rule : rules_) {
        const auto decision = rule->evaluate(request);
        if (!decision.approved) return decision;
    }
    return {true, "rules_passed"};
}
Decision AmountRule::evaluate(const Request& request) const {
    return request.amountCents >= 0 && request.amountCents <= 1000000000
        ? Decision{true, "amount_valid"} : Decision{false, "amount_out_of_range"};
}
Decision SimulationRule::evaluate(const Request& request) const {
    if (request.scenario == "decline") return {false, "simulated_decline"};
    if (request.scenario == "approve" || request.scenario == "timeout") return {true, "simulation_valid"};
    return {false, "unknown_scenario"};
}
}
