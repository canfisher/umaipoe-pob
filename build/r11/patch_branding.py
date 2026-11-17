from pathlib import Path
import json
import re
import shutil

HERE = Path(__file__).parent


def between(text, start, end, replacement):
    a = text.index(start)
    b = text.index(end, a)
    return text[:a] + replacement + text[b:]


def function_body(text, signature, replacement):
    start = text.index(signature)
    opening = text.index('{', start)
    token = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|(?:u8|L)?"(?:[^"\\]|\\.)*"|\x27(?:[^\x27\\]|\\.)*\x27|[{}]')
    depth = 0
    for match in token.finditer(text, opening):
        if match[0] == '{':
            depth += 1
        elif match[0] == '}':
            depth -= 1
            if not depth:
                return text[:opening] + '{\n' + replacement + '\n}' + text[match.end():]
    raise ValueError(signature)


def apply(root):
    host = root / 'host'
    for name in ['umaipoe_brand.h', 'umaipoe_logo.h', 'umaipoe.ico', 'branding_test.cpp']:
        shutil.copy2(HERE / name, host / name)
    history = (HERE / 'umaipoe-history.txt').read_text(encoding='utf-8')
    for name, symbol in [('changelog.h', 'kChangelogText'), ('changelog_en.h', 'kChangelogTextEn')]:
        (host / name).write_text('#pragma once\nstatic const char ' + symbol + '[] =\n' +
            '\n'.join('u8' + json.dumps(line + '\n', ensure_ascii=False) for line in history.splitlines()) + ';\n', encoding='utf-8')
    p = host / 'app_version.h'
    text = p.read_text(encoding='utf-8')
    for key, value in [('MAJOR', 11), ('MINOR', 1), ('PATCH', 0)]:
        text = re.sub(rf'(#define POBTOOLS_VER_{key}) \d+', rf'\g<1> {value}', text)
    p.write_text(text, encoding='utf-8')
    p = host / 'pob-zh.rc'
    text = p.read_text(encoding='utf-8').replace('"pobtools.ico"', '"umaipoe.ico"')
    text = text.replace('"PobTools"', '"Umaipoe PoB"').replace('PobTools - Path of Building zh-TW launcher', 'Umaipoe Korean PoB Tools')
    text = text.replace('"040404B0"', '"041204B0"').replace('0x404, 1200', '0x412, 1200')
    p.write_text(text, encoding='utf-8')
    p = host / 'launcher_ui.cpp'
    text = p.read_text(encoding='utf-8')
    text = text.replace('#include "app_version.h"', '#include "app_version.h"\n#include "umaipoe_brand.h"\n#include "umaipoe_logo.h"')
    text = text.replace('out.push_back(kChangelogTextEn);', 'out.push_back(u8"우마이 응원 페이지 블로그 질문과 피드백 업데이트 안내 다운로드 자동 사용법 복구 방법 보기 배포판의 한국어 도구 실행기 원본 프로그램 번역팩 관리 작업 저장 종료한 뒤 다시 실행하면 적용됩니다");\n\tout.push_back(kChangelogTextEn);')
    text = text.replace('L"PobTools"', 'L"Umaipoe PoB"')
    text = text.replace('"PobTools"', 'u8"우마이 한글 PoB"').replace('"PobTools "', 'u8"우마이 한글 PoB "')
    text = text.replace('L"https://github.com/Hsiung-Shao/PobTools-zh"', 'kUmaipoeRepository')
    text = between(text, 'static const LinkEntry kLinksTools[] = {', '\n};', '''static const LinkEntry kLinksTools[] = {
    { u8"우마이 POE 공략노트", L"https://umaipoe.tistory.com/" },
    { u8"한글 PoB 다운로드·패치노트", kUmaipoeDownload },
    { u8"아틀라스 파밍 검색", L"https://umaipoe.tistory.com/67" },
    { u8"우마이 GitHub", kUmaipoeRepository },''')
    text = text.replace('L"https://www.pathofexile.com/trade"', 'L"https://poe.kakaogames.com/trade/search"')
    text = text.replace('u8"PoeDB 流亡編年史",       L"https://poedb.tw"', 'u8"PoEDB 한국어",       L"https://poedb.tw/kr/"')
    text = text.replace('u8"巴哈姆特 PoE 板",        L"https://forum.gamer.com.tw/A.php?bsn=18966"', 'u8"우마이 POE 공략노트", L"https://umaipoe.tistory.com/"')
    text = text.replace('raw[0] == \'v\'', '(raw[0] == \'r\' || raw[0] == \'v\')')
    text = text.replace('"v" POBTOOLS_VERSION_STRING', 'UMAIPOE_RELEASE')
    text = text.replace('static void DrawLogo(', 'static unsigned umaipoeLogoTexture = 0;\n\nstatic void DrawLogo(', 1)
    text = function_body(text, 'static void DrawLogo(', '''    if (!umaipoeLogoTexture) umaipoeLogoTexture = CreateTextureRGBA(kUmaipoeLogo, 96, 96);
    if (umaipoeLogoTexture) {
        dl->AddImageRounded((ImTextureID)(intptr_t)umaipoeLogoTexture, p, p + ImVec2(size, size),
            ImVec2(0, 0), ImVec2(1, 1), IM_COL32_WHITE, size * 0.22f);
    } else {
        dl->AddRectFilled(p, p + ImVec2(size, size), Tok::AccentSoft, size * 0.22f);
        dl->AddText(p + ImVec2(size * 0.35f, size * 0.25f), Tok::AccentText, "U");
    }''')
    text = text.replace('\tImGui_ImplOpenGL3_Shutdown();\n\tImGui_ImplGlfw_Shutdown();',
        '\tif (umaipoeLogoTexture) { DeleteTexture(umaipoeLogoTexture); umaipoeLogoTexture = 0; }\n\tImGui_ImplOpenGL3_Shutdown();\n\tImGui_ImplGlfw_Shutdown();')
    text = between(text, '\t\t\tif (appUpd) {\n\t\t\t\tconst ImVec2 keep', '\t\t\tImGui::Dummy(ImVec2(inner, logo));', '''            {
                const ImVec2 keep = ImGui::GetCursorScreenPos();
                const float width = PobUi::ButtonWidth(u8"업데이트 안내", PobUi::BtnSize::Sm, PobIcon::ExternalLink);
                ImGui::SetCursorScreenPos(ImVec2(hp.x + inner - width, hp.y + D(6.0f)));
                if (PobUi::Button(u8"업데이트 안내", PobUi::BtnKind::Secondary, PobUi::BtnSize::Sm, PobIcon::ExternalLink))
                    ShellExecuteW(nullptr, L"open", kUmaipoeDownload, nullptr, nullptr, SW_SHOWNORMAL);
                if (ImGui::IsItemHovered()) PobUi::Tooltip(u8"우마이 배포판의 다운로드와 자동 업데이트 사용법을 엽니다.");
                ImGui::SetCursorScreenPos(keep);
            }
''')
    text = between(text, '\t\t\t{\n\t\t\t\tPobUi::RowBegin(S.autoAppUpdate,', '\t\t\tPobUi::CardEnd();\n\n\t\t\t// 4. POB performance', '''            PobUi::Hint(u8"우마이 자동 업데이트는 Umaipoe-PoB.exe에서 관리합니다. 작업을 저장하고 종료한 뒤 다시 실행하면 적용됩니다. 이 도구 실행기는 원본 프로그램이나 번역팩으로 자동 교체하지 않습니다.", cardW - D(32.0f));
            if (PobUi::Link(u8"업데이트·복구 방법 보기"))
                ShellExecuteW(nullptr, L"open", kUmaipoeDownload, nullptr, nullptr, SW_SHOWNORMAL);
''')
    text = text.replace('UmaipoeSupportLink(exeDir);', 'UmaipoeCommunityLinks(exeDir);')
    assert all(s not in text for s in ['Hsiung-Shao', 'hsiung-shao.github.io', 'discord.gg/6VamPQb8nC', '"PobTools"'])
    p.write_text(text, encoding='utf-8')
    p = host / 'launcher_strings_io.cpp'
    text = p.read_text(encoding='utf-8').replace('#include "launcher_strings_io.h"', '#include "launcher_strings_io.h"\n#include "umaipoe_brand.h"')
    text = text.replace('st.s = StringsFor(locale);', 'st.s = StringsFor(locale);\n\tUmaipoeStrings(st.s);')
    text = text.replace('return st;', 'UmaipoeStrings(st.s); return st;')
    # Keep early return conditions scoped after adding the override call.
    text = text.replace('if (!read_file_utf8(slotRoot + locale + L"\\\\launcher.json", content)) UmaipoeStrings(st.s); return st;',
                        'if (!read_file_utf8(slotRoot + locale + L"\\\\launcher.json", content)) { UmaipoeStrings(st.s); return st; }')
    text = text.replace('if (!doc.contains("entries") || !doc["entries"].is_object()) UmaipoeStrings(st.s); return st;',
                        'if (!doc.contains("entries") || !doc["entries"].is_object()) { UmaipoeStrings(st.s); return st; }')
    p.write_text(text, encoding='utf-8')
    p = host / 'app_update.cpp'
    text = p.read_text(encoding='utf-8').replace('"Hsiung-Shao/PobTools-zh"', '"canfisher/umaipoe-pob"')
    text = function_body(text, 'void AppUpdater::Init(', '''    exeDir_ = exeDir;
    std::lock_guard<std::mutex> lock(stMx_);
    st_ = Status{};
    st_.localVer = POBTOOLS_VERSION_STRING;
    st_.localDataVer = ReadLocalDataVersion(exeDir_);
    st_.message = u8"업데이트는 Umaipoe-PoB.exe에서 관리합니다.";''')
    for signature in ['void AppUpdater::RequestCheck(', 'void AppUpdater::StartAppUpdate(', 'void AppUpdater::StartTranslationUpdate(']:
        text = function_body(text, signature, '    return;')
    text = function_body(text, 'int RunAppUpdateCli(', '    printf("Use Umaipoe-PoB.exe. https://umaipoe.tistory.com/66\\n");\n    return 3;')
    text = function_body(text, 'int RunAppFetchTest(', '    return 3;')
    p.write_text(text, encoding='utf-8')
    tool_titles = {
        'atlas_planner.cpp': '아틀라스 전략',
        'filter_editor.cpp': '아이템 필터 편집기',
        'launcher_editor.cpp': '번역 편집기',
        'regex_tool_ui.cpp': '지도 검색식',
        'timeless_jewel_ui.cpp': '무궁한 주얼 검색기',
        'warehouse_ui.cpp': '보관함 수익 기록',
    }
    for name, title in tool_titles.items():
        p = host / name
        text, count = re.subn(r'desc\.titleUtf8 = "[^"\n]*";',
                             f'desc.titleUtf8 = u8"우마이 PoB — {title}";',
                             p.read_text(encoding='utf-8'))
        assert count == 1, name
        p.write_text(text, encoding='utf-8')
    for name in ['host_main.cpp', 'window_manager.cpp', 'pob_protocol.cpp', 'modern_ui_window.cpp', 'tool_window.h']:
        p = host / name
        text = p.read_text(encoding='utf-8')
        text = text.replace('L"PobTools"', 'L"Umaipoe PoB"')
        text = text.replace('L" - PobTools"', 'L" - Umaipoe PoB"')
        text = text.replace('titleUtf8 = "PobTools"', 'titleUtf8 = u8"우마이 PoB"')
        p.write_text(text, encoding='utf-8')
    atlas = (host / 'atlas_planner.cpp').read_text(encoding='utf-8')
    assert all(label in atlas for label in ['아틀라스 전략', '패시브 할당', '계획 모드', '버전 비교'])
    print('Umaipoe branding, history, links and update isolation applied')


if __name__ == '__main__':
    import sys
    apply(Path(sys.argv[1]))
