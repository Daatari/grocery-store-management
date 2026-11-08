#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <map>
#include <stdexcept>
#include <string>

namespace grocery {
using Money = std::int64_t; // Integer cents; no floating-point rounding in storage.
constexpr int maxQuantity = 1000000;
constexpr Money maxPrice = 100000000; // 10,000 lines * max quantity * max price fits int64_t.

struct Product {
    int id;
    std::string department;
    std::string name;
    Money price;
    int stock;
};
struct State {
    std::map<int, Product> products;
    std::map<int, int> cart;
    void swap(State& other) noexcept {
        products.swap(other.products);
        cart.swap(other.cart);
    }
};
class ValidationError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
class StorageError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
void validate(const State& state);
std::string money(Money cents);

class Repository {
public:
    virtual ~Repository() = default;
    virtual State load() = 0;
    // Strong guarantee: a reported failure leaves the previous snapshot intact.
    virtual void save(const State& state) = 0;
};

class FileRepository final : public Repository {
public:
    explicit FileRepository(std::filesystem::path path);
    ~FileRepository() override;
    FileRepository(const FileRepository&) = delete;
    FileRepository& operator=(const FileRepository&) = delete;
    State load() override;
    void save(const State& state) override;
private:
    std::filesystem::path path_;
    std::filesystem::path lock_;
};

struct Event {
    std::string operation;
    std::string level;
    std::string outcome;
    std::string code;
    long long durationUs;
};
class EventSink {
public:
    virtual ~EventSink() = default;
    // Observability failure must never change the result of a committed write.
    virtual void emit(const Event& event) noexcept = 0;
};
class JsonLogger final : public EventSink {
public:
    JsonLogger(std::filesystem::path directory, std::string node);
    void emit(const Event& event) noexcept override;
private:
    std::filesystem::path path_;
    std::string node_;
    std::string session_;
    std::uint64_t sequence_ = 0;
};

class StoreService {
public:
    StoreService(Repository& repository, EventSink& events);
    const State& state() const { return state_; }
    void add(int id, int quantity);
    void remove(int id, int quantity);
    void cancel();
    Money checkout();
    void create(Product product);
    Money total() const;
private:
    void change(const std::string& operation, const std::function<void(State&)>& action);
    Repository& repository_;
    EventSink& events_;
    State state_;
};
} // namespace grocery
