int RunTimelessKoreanSelfTest(const std::wstring& exeDir)
{
    TJDataset ds;
    std::string error, report;
    int failed = 0, passed = 0;
    auto check = [&](bool ok, const std::string& label) {
        report += std::string(ok ? "PASS " : "FAIL ") + label + "\n";
        ok ? ++passed : ++failed;
    };
    if (!load_dataset(exeDir, ds, &error)) return 1;
    auto korean = [](const std::string& value) {
        if (value.empty()) return false;
        for (unsigned char c : value)
            if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '{' || c == '}') return false;
        return true;
    };
    for (const auto& family : ds.conquerors) {
        int seed = ds.seedMin.at(family.first) + (ds.seedMax.at(family.first) - ds.seedMin.at(family.first)) / 2;
        if (family.first == 5) seed *= 20;
        for (int i = 0; i < (int)family.second.size(); ++i) {
            const auto& leader = family.second[i];
            check(korean(leader.nameZh), "conqueror " + leader.name);
            const std::string fixture = u8"아이템 종류: 주얼\n아이템 희귀도: 고유\n아이템 레벨: 84\n--------\n" +
                leader.nameZh + u8" 휘하의 전사 " + std::to_string(seed) + "(100-160000)" + u8"명의 지휘권 통솔\n";
            const auto parsed = TJParsePaste(ds, fixture);
            check(parsed.jewelType == family.first && parsed.conqIndex == i && parsed.seed == seed,
                  "Korean advanced-copy parser " + leader.name);
        }
    }
    auto entries = [&](const std::vector<TJEntry>& values) {
        for (const auto& entry : values) {
            check(korean(entry.dnZh), "entry name " + entry.id);
            check(entry.sd.size() == entry.sdZh.size(), "parallel effects " + entry.id);
            for (const auto& line : entry.sdZh) check(korean(line), "Korean effect " + entry.id);
        }
    };
    entries(ds.additions);
    entries(ds.nodes);
    for (const auto& type : ds.types) {
        const auto templates = TJStatTemplates(ds, type.first);
        check(!templates.empty(), "templates family " + std::to_string(type.first));
        for (const auto& item : templates) check(korean(item.zh), "Korean search option " + item.en);
    }
    TJStatMod regen; regen.fmt = "g"; regen.min = 0.7; regen.max = 1.2;
    check(TJRollStat(u8"1초마다 생명력의 (0.7-1.2)% 재생", "life_regeneration_rate_per_minute_%", regen, 60) ==
          u8"1초마다 생명력의 1% 재생", "Korean regeneration roll retains per-second unit");
    TJStatMod resist; resist.min = 12; resist.max = 15;
    check(TJRollStat(u8"냉기 저항 +(12-15)%", "base_cold_damage_resistance_%", resist, 14) ==
          u8"냉기 저항 +14%", "Korean signed resistance roll");
    report += "PASSED: " + std::to_string(passed) + "\nFAILURES: " + std::to_string(failed) + "\n";
    HANDLE h = CreateFileW((exeDir + L"tj_ko_selftest.txt").c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, 0, nullptr);
    if (h == INVALID_HANDLE_VALUE) return 1;
    DWORD written = 0;
    const BOOL saved = WriteFile(h, report.data(), (DWORD)report.size(), &written, nullptr);
    CloseHandle(h);
    return saved && written == report.size() && failed == 0 ? 0 : 1;
}
