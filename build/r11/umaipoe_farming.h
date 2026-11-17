#pragma once
#include <algorithm>
#include <map>
#include <set>
#include <string>
#include <vector>
#include <json.hpp>

namespace UmaipoeFarm {
using Json = nlohmann::ordered_json;
struct Node { int id; bool small, special, caution; std::vector<int> adjacent; };
struct Category { std::string id, name, note; std::vector<int> targets; };
struct State { std::vector<std::string> selected; int budget = 80; std::set<int> excluded, allowed; };
struct Result { std::vector<int> nodes, targets; std::map<int, std::string> pending; };
struct Catalog {
    std::string version;
    int root = 0, maximum = 150;
    std::map<int, Node> nodes;
    std::vector<Category> categories;
    std::map<int, std::string> names;
    void Load(const Json& j) {
        *this = Catalog{};
        version = j.at("version").get<std::string>();
        root = j.at("root").get<int>(); maximum = j.at("maxPoints").get<int>();
        for (auto it = j.at("nodes").begin(); it != j.at("nodes").end(); ++it) {
            const int id = std::stoi(it.key()); const auto& n = it.value();
            nodes.emplace(id, Node{id, n.value("kind", "") == "small", n.value("special", false), n.value("caution", false), {}});
            names[id] = n.value("ko", "");
            if (names[id].empty()) names[id] = n.value("name", std::to_string(id));
        }
        for (const auto& edge : j.at("edges")) {
            int a = edge.at(0), b = edge.at(1);
            if (nodes.count(a) && nodes.count(b)) { nodes.at(a).adjacent.push_back(b); nodes.at(b).adjacent.push_back(a); }
        }
        for (auto& pair : nodes) std::sort(pair.second.adjacent.begin(), pair.second.adjacent.end());
        for (const auto& c : j.at("categories"))
            categories.push_back({c.at("id"), c.at("name"), c.value("note", ""), c.at("targets").get<std::vector<int>>()});
    }
    const Category* Find(const std::string& id) const {
        for (const auto& c : categories) if (c.id == id) return &c;
        return nullptr;
    }
};
inline bool Influence(const std::string& id) { return id == "exarch" || id == "eater" || id == "maven"; }
inline State Normalize(const Catalog& c, State s) {
    s.budget = std::clamp(s.budget, 0, c.maximum);
    std::set<std::string> seen; bool influence = false;
    s.selected.erase(std::remove_if(s.selected.begin(), s.selected.end(), [&](const std::string& id) {
        if (!c.Find(id) || !seen.insert(id).second) return true;
        if (Influence(id)) { if (influence) return true; influence = true; }
        return false;
    }), s.selected.end());
    s.excluded.erase(c.root);
    return s;
}
inline Json Encode(const State& s) {
    return Json{{"selected", s.selected}, {"budget", s.budget}, {"excluded", s.excluded}, {"allowed", s.allowed}};
}
inline State Decode(const Catalog& c, const std::string& content) {
    State s;
    try {
        const auto j = Json::parse(content);
        if (j.contains("selected") && j["selected"].is_array())
            for (const auto& id : j["selected"]) if (id.is_string()) s.selected.push_back(id.get<std::string>());
        if (j.contains("budget") && j["budget"].is_number_integer()) s.budget = j["budget"].get<int>();
        for (const char* key : {"excluded", "allowed"})
            if (j.contains(key) && j[key].is_array())
                for (const auto& id : j[key]) if (id.is_number_integer() && c.nodes.count(id.get<int>()))
                    (std::string(key) == "excluded" ? s.excluded : s.allowed).insert(id.get<int>());
    } catch (...) {}
    return Normalize(c, s);
}
inline std::map<int, int> Paths(const Catalog& c, const std::set<int>& allocated,
                              const std::set<int>& eligible, const std::set<int>& excluded) {
    std::map<int, int> previous; std::vector<int> queue;
    for (int id : allocated) { previous[id] = id; queue.push_back(id); }
    for (size_t i = 0; i < queue.size(); ++i)
        for (int next : c.nodes.at(queue[i]).adjacent) {
            const auto& node = c.nodes.at(next);
            if (previous.count(next) || excluded.count(next) || node.special || (!node.small && !eligible.count(next))) continue;
            previous[next] = queue[i]; queue.push_back(next);
        }
    return previous;
}
inline std::vector<int> Path(int target, const std::map<int, int>& previous, const std::set<int>& allocated) {
    std::vector<int> path;
    if (!previous.count(target)) return path;
    for (int id = target; !allocated.count(id); id = previous.at(id)) path.push_back(id);
    std::reverse(path.begin(), path.end()); return path;
}
inline Result Calculate(const Catalog& c, State s) {
    s = Normalize(c, s); Result result;
    if (!c.nodes.count(c.root)) return result;
    std::set<int> allocated{c.root}, eligible, wanted;
    for (const auto& id : s.selected)
        for (int node : c.Find(id)->targets) if (c.nodes.count(node)) {
            wanted.insert(node); const auto& n = c.nodes.at(node);
            if (!s.excluded.count(node) && !n.special && (!n.caution || s.allowed.count(node))) eligible.insert(node);
        }
    bool changed = true;
    while (changed) {
        changed = false;
        for (const auto& id : s.selected) {
            const auto previous = Paths(c, allocated, eligible, s.excluded);
            std::vector<int> best; int bestTarget = 0;
            for (int target : c.Find(id)->targets) {
                if (!eligible.count(target) || allocated.count(target)) continue;
                auto path = Path(target, previous, allocated);
                if (path.empty() || allocated.size() - 1 + path.size() > static_cast<size_t>(s.budget)) continue;
                if (best.empty() || path.size() < best.size() || (path.size() == best.size() && target < bestTarget)) {
                    best = std::move(path); bestTarget = target;
                }
            }
            if (best.empty()) continue;
            allocated.insert(best.begin(), best.end()); changed = true;
        }
    }
    const auto previous = Paths(c, allocated, eligible, s.excluded);
    for (int id : wanted) {
        if (allocated.count(id)) { result.targets.push_back(id); continue; }
        result.pending[id] = s.excluded.count(id) ? u8"직접 제외" : c.nodes.at(id).special ? u8"트리에서 직접 선택"
            : !eligible.count(id) ? u8"위험도 확인 후 허용" : previous.count(id) ? u8"포인트 부족" : u8"현재 선택으로 연결 불가";
    }
    allocated.erase(c.root); result.nodes.assign(allocated.begin(), allocated.end()); return result;
}
}
