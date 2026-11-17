#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include "umaipoe_farming.h"
#include "atlas_persist.h"

static void check(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
static UmaipoeFarm::Json read(const std::string& path) { std::ifstream file(path); UmaipoeFarm::Json value; file >> value; return value; }
int main(int argc, char** argv) {
    try {
        check(argc == 3, "expected catalog and fixture paths");
        const auto begin = std::chrono::steady_clock::now();
        UmaipoeFarm::Catalog catalog; catalog.Load(read(argv[1]));
        const auto cases = read(argv[2]); size_t count = 0;
        for (const auto& test : cases) {
            const auto state = UmaipoeFarm::Decode(catalog, test["input"].dump());
            const auto result = UmaipoeFarm::Calculate(catalog, state);
            check(result.nodes == test["expected"].get<std::vector<int>>(), ("blog graph mismatch at case " + std::to_string(count)).c_str());
            check(result.nodes.size() <= static_cast<size_t>(state.budget), "budget exceeded");
            std::set<int> allocated(result.nodes.begin(), result.nodes.end()), visited{catalog.root};
            std::vector<int> queue{catalog.root};
            for (size_t i = 0; i < queue.size(); ++i) for (int next : catalog.nodes.at(queue[i]).adjacent)
                if (allocated.count(next) && visited.insert(next).second) queue.push_back(next);
            check(visited.size() == allocated.size() + 1, "disconnected allocation");
            for (int id : result.nodes) check(!state.excluded.count(id) && !catalog.nodes.at(id).special, "excluded or manual-only node allocated");
            check(UmaipoeFarm::Calculate(catalog, UmaipoeFarm::Decode(catalog, UmaipoeFarm::Encode(state).dump())).nodes == result.nodes, "settings roundtrip changed result");
            ++count;
        }
        AtlasBuildFile original;
        original.AddBuild(u8"기존 전략 · 보존"); original.Active().alloc = {123, 456}; original.Active().notes = u8"원본 메모";
        const auto preserved = AtlasExportJson(original.Active(), "3.30.0");
        AtlasBuildFile generated = original;
        generated.active = generated.AddBuild(u8"탐험 + 군단");
        auto state = UmaipoeFarm::Decode(catalog, R"({"selected":["expedition","legion","eater"],"budget":100,"excluded":[123]})");
        generated.Active().farming = UmaipoeFarm::Encode(state).dump();
        generated.Active().alloc = UmaipoeFarm::Calculate(catalog, state).nodes;
        generated.Active().variants = {{3926,2215}};
        AtlasBuildFile reloaded;
        check(reloaded.ParseDoc(generated.SerializeDoc()), "project parse failed");
        check(reloaded.Active().farming == generated.Active().farming && reloaded.Active().alloc == generated.Active().alloc, "project roundtrip failed");
        check(AtlasExportJson(reloaded.builds.at(0), "3.30.0") == preserved, "original project changed");
        AtlasBuildEntry shared; std::string error;
        check(AtlasParseShareCode(AtlasBuildShareCode(generated.Active(), "3.30.0"), &shared, &error), "share parse failed");
        check(shared.farming == generated.Active().farming && shared.alloc == generated.Active().alloc && shared.variants == generated.Active().variants, "share roundtrip failed");
        wchar_t buffer[MAX_PATH]; GetTempPathW(MAX_PATH, buffer);
        const std::wstring dir = std::wstring(buffer) + L"Umaipoe-파밍검사-" + std::to_wstring(GetCurrentProcessId()) + L"\\";
        check(CreateDirectoryW(dir.c_str(), nullptr) != 0, "test directory failed");
        check(original.Save(dir), "first save failed");
        const auto file = AtlasBuildFile::PathOf(dir);
        HANDLE lock = CreateFileW(file.c_str(), GENERIC_READ, 0, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        check(lock != INVALID_HANDLE_VALUE, "test lock failed");
        check(!generated.Save(dir), "locked destination unexpectedly saved"); CloseHandle(lock);
        AtlasBuildFile afterFailure;
        check(afterFailure.Load(dir) && afterFailure.SerializeDoc() == original.SerializeDoc(), "failed save damaged original");
        check(generated.Save(dir) && reloaded.Load(dir) && reloaded.SerializeDoc() == generated.SerializeDoc(), "disk save/load failed");
        check(GetFileAttributesW((file + L".bak").c_str()) != INVALID_FILE_ATTRIBUTES, "backup missing");
        DeleteFileW(file.c_str()); DeleteFileW((file + L".bak").c_str());
        RemoveDirectoryW((dir + L"PobTools").c_str()); RemoveDirectoryW(dir.c_str());
        std::cout << "PASS " << count << " graph cases; original preservation, Korean paths, sharing, save/load, locked-save rollback and backup; "
            << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-begin).count() << " ms\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
