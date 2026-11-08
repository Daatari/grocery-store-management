#include "store.hpp"
#include <chrono>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <utility>

namespace grocery {
namespace {
std::string sessionId() {
    std::random_device random;
    std::ostringstream out;
    for (int i = 0; i < 4; ++i) out << std::hex << std::setw(8) << std::setfill('0') << random();
    return out.str();
}
std::string timestamp() {
    const auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    std::tm utc{};
#ifdef _WIN32
    gmtime_s(&utc, &now);
#else
    gmtime_r(&now, &utc);
#endif
    std::ostringstream out;
    out << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}
std::string json(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c);
        else out << c;
    }
    out << '"';
    return out.str();
}
}
JsonLogger::JsonLogger(std::filesystem::path directory, std::string node)
    : node_(std::move(node)), session_(sessionId()) {
    if (node_.empty() || node_.size() > 64 || node_.find_first_not_of(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") != std::string::npos)
        throw ValidationError("Node must contain 1-64 letters, digits, underscores, or hyphens.");
    std::filesystem::create_directories(directory);
    path_ = directory / (node_ + "-" + session_ + ".jsonl");
    std::ofstream out(path_, std::ios::app);
    if (!out) throw StorageError("Cannot open log file.");
}
void JsonLogger::emit(const Event& event) noexcept {
    try {
        const auto id = session_ + "-" + std::to_string(++sequence_);
        std::ofstream out(path_, std::ios::app);
        out << "{\"schema_version\":1,\"event_id\":" << json(id)
            << ",\"request_id\":" << json(id) << ",\"timestamp\":" << json(timestamp())
            << ",\"node\":" << json(node_) << ",\"service\":\"grocery\",\"operation\":" << json(event.operation)
            << ",\"level\":" << json(event.level) << ",\"outcome\":" << json(event.outcome)
            << ",\"code\":" << json(event.code) << ",\"duration_us\":" << event.durationUs << "}\n";
        out.flush();
        if (!out) std::cerr << "Warning: event log write failed; operation result is unchanged.\n";
    } catch (...) {
        std::cerr << "Warning: event logging unavailable; operation result is unchanged.\n";
    }
}
} // namespace grocery
