#include "store.hpp"
#include <chrono>
#include <iomanip>
#include <sstream>

namespace grocery {
namespace {
bool validName(const std::string& name) {
    if (name.empty() || name.size() > 120) return false;
    bool visible = false;
    for (unsigned char c : name) {
        if (c < 32 || c == 127) return false;
        if (c != ' ') visible = true;
    }
    return visible;
}
void quantity(int value) {
    if (value <= 0 || value > maxQuantity)
        throw ValidationError("Quantity must be between 1 and 1000000.");
}
Product& product(State& state, int id) {
    const auto found = state.products.find(id);
    if (found == state.products.end()) throw ValidationError("Unknown product ID.");
    return found->second;
}
}
void validate(const State& state) {
    if (state.products.size() > 10000) throw ValidationError("Product limit exceeded.");
    for (const auto& [id, p] : state.products) {
        if (id <= 0 || id != p.id || !validName(p.name) || !validName(p.department) ||
            p.price < 0 || p.price > maxPrice || p.stock < 0 || p.stock > maxQuantity)
            throw ValidationError("Invalid product record.");
    }
    for (const auto& [id, count] : state.cart) {
        quantity(count);
        const auto found = state.products.find(id);
        if (found == state.products.end()) throw ValidationError("Cart references unknown product.");
        if (found->second.stock > maxQuantity - count)
            throw ValidationError("Stock plus reserved quantity exceeds limit.");
    }
}
std::string money(Money cents) {
    std::ostringstream out;
    out << '$' << cents / 100 << '.' << std::setw(2) << std::setfill('0') << cents % 100;
    return out.str();
}
StoreService::StoreService(Repository& repository, EventSink& events)
    : repository_(repository), events_(events) {
    try {
        state_ = repository_.load();
        validate(state_);
        events_.emit({"store.load", "INFO", "success", "ok", 0});
    } catch (...) {
        events_.emit({"store.load", "ERROR", "failure", "load_failed", 0});
        throw;
    }
}
void StoreService::change(const std::string& operation, const std::function<void(State&)>& action) {
    const auto start = std::chrono::steady_clock::now();
    auto log = [&](const char* level, const char* outcome, const char* code) {
        auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - start).count();
        events_.emit({operation, level, outcome, code, elapsed});
    };
    try {
        State next = state_;
        action(next);
        validate(next);
        repository_.save(next);
        state_.swap(next); // No throwing operations after the persistence commit.
    } catch (const ValidationError&) {
        log("WARN", "rejected", "validation_failed");
        throw;
    } catch (const std::exception&) {
        log("ERROR", "failure", "storage_or_internal_error");
        throw;
    }
    log("INFO", "success", "ok");
}
void StoreService::add(int id, int count) {
    change("cart.add", [&](State& next) {
        quantity(count);
        auto& p = product(next, id);
        if (count > p.stock) throw ValidationError("Insufficient stock.");
        next.cart[id] += count;
        p.stock -= count;
    });
}
void StoreService::remove(int id, int count) {
    change("cart.remove", [&](State& next) {
        quantity(count);
        auto found = next.cart.find(id);
        if (found == next.cart.end() || count > found->second)
            throw ValidationError("Quantity exceeds the cart line.");
        product(next, id).stock += count;
        found->second -= count;
        if (found->second == 0) next.cart.erase(found);
    });
}
void StoreService::cancel() {
    change("cart.cancel", [](State& next) {
        for (const auto& [id, count] : next.cart) next.products.at(id).stock += count;
        next.cart.clear();
    });
}
Money StoreService::total() const {
    Money result = 0;
    for (const auto& [id, count] : state_.cart)
        result += state_.products.at(id).price * count;
    return result; // Bounds in validate keep the maximum below int64_t capacity.
}
Money StoreService::checkout() {
    const Money subtotal = total();
    change("cart.checkout", [](State& next) {
        if (next.cart.empty()) throw ValidationError("Cart is empty.");
        next.cart.clear(); // Stock was reserved by add; do not deduct twice.
    });
    return subtotal;
}
void StoreService::create(Product p) {
    change("inventory.create", [&](State& next) {
        if (!next.products.emplace(p.id, p).second)
            throw ValidationError("Product ID already exists.");
    });
}
} // namespace grocery
