#include "store.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <vector>

using namespace grocery;
namespace fs = std::filesystem;
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class Exception, class Action> void rejects(Action action) {
    try { action(); } catch (const Exception&) { return; }
    throw std::runtime_error("Expected exception was not thrown.");
}
struct MemoryRepository : Repository {
    State saved{{{1, {1, "Produce", "Apples", 399, 16}}}, {}};
    bool fail = false;
    State load() override { return saved; }
    void save(const State& value) override {
        if (fail) throw StorageError("Injected write failure");
        saved = value;
    }
};
struct RecordingSink : EventSink {
    std::vector<Event> events;
    void emit(const Event& event) noexcept override { events.push_back(event); }
};
void businessTests() {
    MemoryRepository repo;
    RecordingSink sink;
    StoreService store(repo, sink);
    store.add(1, 5);
    store.remove(1, 2);
    require(store.state().cart.at(1) == 3 && store.state().products.at(1).stock == 13,
            "Partial removal must retain remaining quantity and restore only removed stock");
    require(store.total() == 1197, "Totals must be exact cents");
    rejects<ValidationError>([&] { store.add(1, 100); });
    rejects<ValidationError>([&] { store.add(1, -1); });
    rejects<ValidationError>([&] { store.add(999, 1); });
    rejects<ValidationError>([&] { store.remove(1, 4); });
    rejects<ValidationError>([&] { store.create({1, "Dairy", "Milk", 100, 2}); });
    require(store.state().cart.at(1) == 3, "Rejected operations must not mutate cart");
    repo.fail = true;
    rejects<StorageError>([&] { store.remove(1, 1); });
    require(repo.saved.cart.at(1) == 3 && store.state().cart.at(1) == 3,
            "Failed persistence must leave memory and disk state unchanged");
    require(sink.events.back().level == "ERROR", "Persistence failure must be observable");
    repo.fail = false;
    StoreService restarted(repo, sink);
    require(restarted.state().cart.at(1) == 3, "Restart must restore active cart");
    require(restarted.checkout() == 1197, "Checkout returns subtotal");
    require(restarted.state().cart.empty() && restarted.state().products.at(1).stock == 13,
            "Checkout must not deduct stock twice");
    rejects<ValidationError>([&] { restarted.checkout(); });
    restarted.add(1, 4);
    restarted.cancel();
    require(restarted.state().products.at(1).stock == 13, "Cancel restores reservations");
    restarted.create({2, "Other", "Apples", 100, 10});
    restarted.add(2, 2);
    require(restarted.state().cart.count(1) == 0, "Same names in different departments must not merge");
    rejects<ValidationError>([&] { restarted.create({3, "", "Invalid", 100, 1}); });
    rejects<ValidationError>([&] { restarted.create({3, "Dept", "Invalid", maxPrice + 1, 1}); });
}
void fileTests(const fs::path& root) {
    const auto path = root / "store.txt";
    State initial{{{1, {1, "Fresh Produce", "Red \"Apples\"", 399, 16}}}, {}};
    {
        FileRepository repo(path);
        require(repo.load().products.empty(), "Missing store must start empty");
        rejects<StorageError>([&] { FileRepository second(path); });
        repo.save(initial);
        require(repo.load().products.at(1).name == "Red \"Apples\"", "Quoted names must round trip");
        fs::create_directory(path.string() + ".tmp");
        rejects<StorageError>([&] { repo.save({}); });
        require(repo.load().products.size() == 1, "Write failure must retain previous snapshot");
    }
    require(!fs::exists(path.string() + ".lock"), "Normal shutdown must release lock");
    const std::vector<std::string> malformed = {
        "GROCERY 2\nEND\n", "GROCERY 1\n", "GROCERY 1\nC 99 1\nEND\n",
        "GROCERY 1\nP 1 D A 100 1\nP 1 D B 200 1\nEND\n",
        "GROCERY 1\nP 1 D A 100 -1\nEND\n", "GROCERY 1\nEND\nextra\n",
        "GROCERY 1\nP 1 D A 100 1 trailing\nEND\n"
    };
    for (const auto& content : malformed) {
        { std::ofstream out(path); out << content; }
        FileRepository repo(path);
        rejects<StorageError>([&] { repo.load(); });
    }
}
int main() {
    auto root = fs::current_path() / ("grocery-tests-" + std::to_string(
        std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directories(root);
    try {
        businessTests();
        fileTests(root);
        fs::remove_all(root); // Only this test's newly created temporary directory.
        std::cout << "Business rules, rollback, restart, locking, and malformed snapshots passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\nTest files retained at " << root << '\n';
        return 1;
    }
}
