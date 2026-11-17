#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <string>

namespace UmaipoeNavigation {
inline constexpr wchar_t kHome[] = L"Umaipoe.Home";
inline constexpr wchar_t kHomeRequest[] = L"Umaipoe.HomeRequested";

inline std::wstring SelfPath() {
    wchar_t path[32768]{};
    DWORD n = GetModuleFileNameW(nullptr, path, 32768);
    return n && n < 32768 ? std::wstring(path, n) : std::wstring();
}
inline bool SameExecutable(HWND window, const std::wstring& path) {
    DWORD pid = 0; GetWindowThreadProcessId(window, &pid);
    HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!process) return false;
    wchar_t candidate[32768]{}; DWORD size = 32768;
    bool same = QueryFullProcessImageNameW(process, 0, candidate, &size) &&
                _wcsicmp(path.c_str(), candidate) == 0;
    CloseHandle(process); return same;
}
inline HWND Find(const wchar_t* key) {
    struct Search { const wchar_t* key; std::wstring path; HWND found; } search{key, SelfPath(), nullptr};
    if (search.path.empty()) return nullptr;
    EnumWindows([](HWND window, LPARAM value) -> BOOL {
        auto& s = *reinterpret_cast<Search*>(value);
        if (GetPropW(window, s.key) && SameExecutable(window, s.path)) {
            s.found = window; return FALSE;
        }
        return TRUE;
    }, reinterpret_cast<LPARAM>(&search));
    return search.found;
}
inline bool Raise(HWND window) {
    if (!IsWindow(window)) return false;
    ShowWindow(window, IsIconic(window) ? SW_RESTORE : SW_SHOW);
    SetForegroundWindow(window);
    if (GetForegroundWindow() != window) {
        FLASHWINFO flash{sizeof(flash), window, FLASHW_TRAY, 2, 0}; FlashWindowEx(&flash);
    }
    return true;
}
inline std::wstring ToolKey(const char* id) {
    std::wstring result = L"Umaipoe.Tool.";
    for (; id && *id; ++id) result += static_cast<unsigned char>(*id);
    return result;
}
inline const char* PanelForFlag(const wchar_t* flag) {
    if (!flag) return nullptr;
    if (!wcscmp(flag, L"--atlas")) return "atlas";
    if (!wcscmp(flag, L"--timeless-jewel")) return "tj";
    if (!wcscmp(flag, L"--filter-editor")) return "filter";
    if (!wcscmp(flag, L"--regex")) return "regex";
    if (!wcscmp(flag, L"--warehouse")) return "warehouse";
    if (!wcscmp(flag, L"--translation-editor")) return "trans";
    return nullptr;
}
inline bool OpenHome(const std::wstring& directory) {
    if (HWND home = Find(kHome)) {
        SetPropW(home, kHomeRequest, reinterpret_cast<HANDLE>(1));
        return Raise(home);
    }
    static ULONGLONG started = 0;
    ULONGLONG now = GetTickCount64();
    if (started && now - started < 5000) return true;
    std::wstring path = SelfPath(), command = L"\"" + path + L"\" --home";
    if (path.empty()) return false;
    STARTUPINFOW startup{sizeof(startup)}; PROCESS_INFORMATION process{};
    if (!CreateProcessW(path.c_str(), &command[0], nullptr, nullptr, FALSE, 0,
                        nullptr, directory.c_str(), &startup, &process)) return false;
    CloseHandle(process.hThread); CloseHandle(process.hProcess); started = now;
    return true;
}
}
