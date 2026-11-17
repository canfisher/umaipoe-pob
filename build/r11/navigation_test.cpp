#include "umaipoe_navigation.h"
#include <cstdio>
#include <cstring>

int main() {
    using namespace UmaipoeNavigation;
    int failed = 0, passed = 0;
    auto check = [&](bool ok, const char* label) { printf("%s %s\n", ok ? "PASS" : "FAIL", label); ok ? ++passed : ++failed; };
    WNDCLASSW cls{}; cls.lpfnWndProc = DefWindowProcW; cls.hInstance = GetModuleHandleW(nullptr); cls.lpszClassName = L"UmaipoeNavigationTest";
    RegisterClassW(&cls);
    HWND home = CreateWindowW(cls.lpszClassName, L"home", 0, 0, 0, 10, 10, nullptr, nullptr, cls.hInstance, nullptr);
    HWND tool = CreateWindowW(cls.lpszClassName, L"tool", 0, 0, 0, 10, 10, nullptr, nullptr, cls.hInstance, nullptr);
    check(home && tool, "hidden test windows created");
    check(Find(kHome) == nullptr, "unmarked window is not a home");
    SetPropW(home, kHome, reinterpret_cast<HANDLE>(1));
    check(Find(kHome) == home, "home discovery uses same executable");
    check(!SameExecutable(home, L"C:\\different-version\\pob-zh.exe"), "other version path rejected");
    auto key = ToolKey("tj"); SetPropW(tool, key.c_str(), reinterpret_cast<HANDLE>(1));
    check(Find(key.c_str()) == tool, "existing jewel window discovered");
    check(Find(ToolKey("atlas").c_str()) == nullptr, "different tool remains independent");
    const wchar_t* flags[] = {L"--atlas", L"--timeless-jewel", L"--filter-editor", L"--regex", L"--warehouse", L"--translation-editor"};
    const char* ids[] = {"atlas", "tj", "filter", "regex", "warehouse", "trans"};
    for (int i = 0; i < 6; ++i) check(!strcmp(PanelForFlag(flags[i]), ids[i]), ids[i]);
    check(!PanelForFlag(nullptr) && !PanelForFlag(L"--engine"), "unknown flags never reuse a tool");
    SetPropW(home, kHomeRequest, reinterpret_cast<HANDLE>(1));
    check(RemovePropW(home, kHomeRequest) != nullptr && !GetPropW(home, kHomeRequest), "home request consumed once");
    DestroyWindow(tool); check(Find(key.c_str()) == nullptr, "closed tool is not reused");
    DestroyWindow(home); check(Find(kHome) == nullptr, "closed home can be reopened");
    printf("PASSED: %d\nFAILURES: %d\n", passed, failed);
    return failed ? 1 : 0;
}
