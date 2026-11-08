#include "store.hpp"
#include <fstream>
#include <iomanip>
#include <sstream>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

namespace grocery {
namespace fs = std::filesystem;
FileRepository::FileRepository(fs::path path) {
    const auto absolute = fs::absolute(path).lexically_normal();
    fs::create_directories(absolute.parent_path());
    // Canonicalize the existing parent first; a new store has no file to resolve.
    path_ = fs::canonical(absolute.parent_path()) / absolute.filename();
    if (fs::exists(path_)) path_ = fs::canonical(path_);
    lock_ = path_.string() + ".lock";
    fs::create_directories(path_.parent_path());
    if (!fs::create_directory(lock_))
        throw StorageError("Store is locked. See docs/operations.md before removing a stale lock.");
}
FileRepository::~FileRepository() {
    std::error_code ignored;
    fs::remove(lock_, ignored);
}
State FileRepository::load() {
    if (!fs::exists(path_)) return {};
    if (fs::file_size(path_) > 8 * 1024 * 1024)
        throw StorageError("Snapshot exceeds 8 MiB limit.");
    std::ifstream in(path_);
    if (!in) throw StorageError("Cannot open store snapshot.");
    std::string line;
    if (!std::getline(in, line) || line != "GROCERY 1")
        throw StorageError("Unsupported snapshot header.");
    State state;
    bool ended = false;
    while (std::getline(in, line)) {
        if (ended) throw StorageError("Unexpected data after snapshot footer.");
        if (line == "END") { ended = true; continue; }
        std::istringstream record(line);
        char type = 0;
        record >> type;
        if (type == 'P') {
            Product p{};
            if (!(record >> p.id >> std::quoted(p.department) >> std::quoted(p.name) >> p.price >> p.stock) ||
                !state.products.emplace(p.id, p).second)
                throw StorageError("Malformed or duplicate product record.");
        } else if (type == 'C') {
            int id = 0, count = 0;
            if (!(record >> id >> count) || !state.cart.emplace(id, count).second)
                throw StorageError("Malformed or duplicate cart record.");
        } else throw StorageError("Unknown snapshot record.");
        record >> std::ws;
        if (!record.eof()) throw StorageError("Unexpected snapshot fields.");
        if (state.products.size() > 10000 || state.cart.size() > 10000)
            throw StorageError("Snapshot record limit exceeded.");
    }
    if (in.bad() || !ended) throw StorageError("Incomplete store snapshot.");
    try { validate(state); }
    catch (const ValidationError&) { throw StorageError("Snapshot violates inventory constraints."); }
    return state;
}
void FileRepository::save(const State& state) {
    validate(state);
    const fs::path temporary = path_.string() + ".tmp";
    try {
        std::ofstream out(temporary, std::ios::trunc);
        if (!out) throw StorageError("Cannot create temporary snapshot.");
        out << "GROCERY 1\n";
        for (const auto& [id, p] : state.products)
            out << "P " << id << ' ' << std::quoted(p.department) << ' ' << std::quoted(p.name)
                << ' ' << p.price << ' ' << p.stock << '\n';
        for (const auto& [id, count] : state.cart) out << "C " << id << ' ' << count << '\n';
        out << "END\n";
        out.flush();
        if (!out) throw StorageError("Cannot write complete snapshot.");
        out.close();
        if (!out) throw StorageError("Cannot close snapshot.");
        // Same-directory replacement: never expose half of an inventory/cart update.
#ifdef _WIN32
        if (!MoveFileExW(temporary.c_str(), path_.c_str(), MOVEFILE_REPLACE_EXISTING))
            throw StorageError("Cannot replace store snapshot.");
#else
        fs::rename(temporary, path_);
#endif
    } catch (...) {
        std::error_code ignored;
        fs::remove(temporary, ignored);
        throw;
    }
}
} // namespace grocery
