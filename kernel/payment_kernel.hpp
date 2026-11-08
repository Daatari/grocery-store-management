#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace payment {
struct Request { std::int64_t amountCents; std::string scenario; };
struct Decision { bool approved; std::string code; };
class Rule {
public:
    virtual ~Rule() = default;
    virtual Decision evaluate(const Request& request) const = 0;
};
// A small plugin host: rules have no knowledge of HTTP, persistence, or the caller.
class Kernel {
public:
    void install(std::unique_ptr<Rule> rule);
    Decision evaluate(const Request& request) const;
private:
    std::vector<std::unique_ptr<Rule>> rules_;
};
class AmountRule final : public Rule {
public:
    Decision evaluate(const Request& request) const override;
};
class SimulationRule final : public Rule {
public:
    Decision evaluate(const Request& request) const override;
};
}
