#include "umaipoe_brand.h"
#include "umaipoe_logo.h"
#include "changelog.h"
#include "changelog_en.h"
#include <cstring>
#include <cwchar>
#include <cstdio>

int main()
{
    LauncherStrings s = STR_EN;
    UmaipoeStrings(s);
    int failures = 0;
    auto check = [&](bool ok, const char* name) {
        printf("%s %s\n", ok ? "PASS" : "FAIL", name);
        failures += !ok;
    };
    check(strcmp(UMAIPOE_RELEASE, "r12") == 0, "release-name");
    check(strstr(s.appSubtitle, u8"우마이") != nullptr, "brand-overrides-defaults");
    check(strstr(s.aboutBody, "Traditional Chinese") == nullptr, "no-original-promotion");
    check(strcmp(s.clCurrent, u8"현재 버전") == 0, "current-label-korean");
    check(strstr(kChangelogTextEn, "r12 (2026-11-18)") == kChangelogTextEn, "current-release-first");
    check(strstr(kChangelogTextEn, "v1.8.7") == nullptr, "original-history-removed");
    check(strcmp(kChangelogText, kChangelogTextEn) == 0, "locale-history-consistent");
    check(sizeof(kUmaipoeLogo) == 96 * 96 * 4, "logo-rgba-size");
    check(wcscmp(kUmaipoeDownload, L"https://umaipoe.tistory.com/66") == 0, "own-download-page");
    check(wcscmp(kUmaipoeRepository, L"https://github.com/canfisher/umaipoe-pob") == 0, "own-repository");
    return failures ? 1 : 0;
}
