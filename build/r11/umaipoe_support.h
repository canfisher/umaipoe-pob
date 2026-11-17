#pragma once
#include "ui_widgets.h"
#include <windows.h>
#include <shellapi.h>
#include <json.hpp>
#include <string>

inline void UmaipoeSupportLink(const std::wstring& root)
{
    static std::wstring url;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        HANDLE file = CreateFileW((root + L"umaipoe-support.json").c_str(), GENERIC_READ,
            FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file != INVALID_HANDLE_VALUE) {
            LARGE_INTEGER size{};
            if (GetFileSizeEx(file, &size) && size.QuadPart > 0 && size.QuadPart <= 16384) {
                std::string content(static_cast<size_t>(size.QuadPart), '\0');
                DWORD read = 0;
                if (ReadFile(file, content.data(), static_cast<DWORD>(content.size()), &read, nullptr)
                    && read == content.size()) {
                    try {
                        std::string value = nlohmann::json::parse(content).value("url", "");
                        if (value.rfind("https://", 0) == 0 && value.size() <= 2048
                            && value.find_first_of("\r\n\t ") == std::string::npos) {
                            int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
                            if (n > 0) {
                                url.resize(n);
                                MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), url.data(), n);
                            }
                        }
                    } catch (...) {}
                }
            }
            CloseHandle(file);
        }
    }
    if (!url.empty() && PobUi::Link(u8"우마이 응원 페이지"))
        ShellExecuteW(nullptr, L"open", url.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

inline void UmaipoeCommunityLinks(const std::wstring& root)
{
    if (PobUi::Link(u8"우마이 블로그 · 질문과 피드백"))
        ShellExecuteW(nullptr, L"open", L"https://umaipoe.tistory.com/66", nullptr, nullptr, SW_SHOWNORMAL);
    UmaipoeSupportLink(root);
}
