from pathlib import Path
import shutil

HERE = Path(__file__).parent

def replace(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)

def apply(root):
    host = root / 'host'
    shutil.copy2(HERE / 'umaipoe_navigation.h', host / 'umaipoe_navigation.h')
    shutil.copy2(HERE / 'navigation_test.cpp', host / 'navigation_test.cpp')
    p = host / 'tool_window.cpp'
    text = p.read_text(encoding='utf-8')
    text = text.replace('#include "tool_window.h"', '#include "tool_window.h"\n#include "umaipoe_navigation.h"')
    text = replace(text, '\tglfwMakeContextCurrent(win);', '''    const std::wstring navigationKey = UmaipoeNavigation::ToolKey(panel.PanelId());
    SetPropW(glfwGetWin32Window(win), navigationKey.c_str(), reinterpret_cast<HANDLE>(1));
\tglfwMakeContextCurrent(win);''')
    text = replace(text, '\t\t\t\tpanel.Frame();', '''                if (PobUi::Button(u8"홈으로", PobUi::BtnKind::Secondary, PobUi::BtnSize::Sm, PobIcon::House)) {
                    if (!UmaipoeNavigation::OpenHome(exeDir))
                        PobUi::ShowToast(u8"홈 창을 열지 못했습니다. 현재 작업은 유지됩니다.", PobUi::Tone::Bad);
                }
                ImGui::SameLine();
                ImGui::TextDisabled(u8"현재 작업을 유지한 채 홈으로 이동합니다");
                ImGui::Separator();
                panel.Frame();''')
    text = replace(text, '\tglfwDestroyWindow(win);', '\tRemovePropW(glfwGetWin32Window(win), navigationKey.c_str());\n\tglfwDestroyWindow(win);')
    p.write_text(text, encoding='utf-8')
    p = host / 'launcher_ui.cpp'
    text = p.read_text(encoding='utf-8')
    text = text.replace('#include "umaipoe_brand.h"', '#include "umaipoe_brand.h"\n#include "umaipoe_navigation.h"')
    text = replace(text, '\tglfwMakeContextCurrent(win);', '\tSetPropW(glfwGetWin32Window(win), UmaipoeNavigation::kHome, reinterpret_cast<HANDLE>(1));\n\tglfwMakeContextCurrent(win);')
    text = replace(text, '\t\tunsigned long pid = 0;\n\t\tif (!PobLaunch::SpawnToolDetached', '''        if (!tabbed) {
            if (const char* id = UmaipoeNavigation::PanelForFlag(flag)) {
                if (HWND existing = UmaipoeNavigation::Find(UmaipoeNavigation::ToolKey(id).c_str())) {
                    UmaipoeNavigation::Raise(existing); return;
                }
            }
            for (const auto& instance : PobLaunch::RunningInstances()) {
                if (instance.kind == kind) {
                    if (instance.hwnd) UmaipoeNavigation::Raise(static_cast<HWND>(instance.hwnd));
                    return;
                }
            }
        }
\t\tunsigned long pid = 0;
\t\tif (!PobLaunch::SpawnToolDetached''')
    text = replace(text, '&CreateTranslationEditorPanel, nullptr, PobLaunch::InstanceKind::Pob, S.editor', '&CreateTranslationEditorPanel, L"--translation-editor", PobLaunch::InstanceKind::TranslationEditor, S.editor')
    text = replace(text, '\t\tbool tabsOk = false;', '''        if (RemovePropW(glfwGetWin32Window(win), UmaipoeNavigation::kHomeRequest)) {
            launcherTabForce = true; pageForce = 0;
        }
\t\tbool tabsOk = false;''')
    text = replace(text, '\t\t\t\t\tep.panel->Frame();', '''                    if (PobUi::Button(u8"홈으로", PobUi::BtnKind::Secondary, PobUi::BtnSize::Sm, PobIcon::House)) {
                        launcherTabForce = true; pageForce = 0;
                    }
                    ImGui::SameLine(); ImGui::TextDisabled(u8"탭과 현재 작업은 유지됩니다");
                    ImGui::Separator();
\t\t\t\t\tep.panel->Frame();''')
    text = replace(text, '\tglfwDestroyWindow(win);', '\tRemovePropW(glfwGetWin32Window(win), UmaipoeNavigation::kHome);\n\tglfwDestroyWindow(win);')
    p.write_text(text, encoding='utf-8')
    p = host / 'host_main.cpp'
    text = p.read_text(encoding='utf-8')
    text = text.replace('#include "launcher_ui.h"', '#include "launcher_ui.h"\n#include "umaipoe_navigation.h"')
    text = replace(text, '\tPobLaunch::RelaunchMarker pending = take_relaunch_marker(dir);', '''    if (arg1 == L"--home") {
        if (HWND home = UmaipoeNavigation::Find(UmaipoeNavigation::kHome)) {
            SetPropW(home, UmaipoeNavigation::kHomeRequest, reinterpret_cast<HANDLE>(1));
            UmaipoeNavigation::Raise(home); return 0;
        }
    }
\tPobLaunch::RelaunchMarker pending = arg1 == L"--home" ? PobLaunch::RelaunchMarker{} : take_relaunch_marker(dir);''')
    p.write_text(text, encoding='utf-8')
    print('Home navigation added to standalone and embedded tools; existing windows reused')
