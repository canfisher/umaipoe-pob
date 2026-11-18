from pathlib import Path

def apply(root):
    host = root / "host"
    # SimpleGraphic retains the callback argument after EnumResourceNamesW.
    # A numeric resource identifier remains valid after the callback returns.
    for name, old, new in (
        ("pob-zh.rc", 'GLFW_ICON ICON "umaipoe.ico"', '101 ICON "umaipoe.ico"'),
        ("modern_ui_window.cpp", 'LoadIconW(hInst, L"GLFW_ICON")', 'LoadIconW(hInst, MAKEINTRESOURCEW(101))'),
    ):
        p=host/name
        text=p.read_text(encoding="utf-8")
        assert text.count(old)==1
        p.write_text(text.replace(old,new),encoding="utf-8")
    p=host/"umaipoe_navigation.h"
    text=p.read_text(encoding="utf-8")
    marker="namespace UmaipoeNavigation {"
    assert text.count(marker)==1
    p.write_text(text.replace(marker,marker+'''
inline void SetWindowIcons(HWND window) {
    for (int small = 0; small <= 1; ++small) {
        HANDLE icon = LoadImageW(GetModuleHandleW(nullptr), MAKEINTRESOURCEW(101), IMAGE_ICON,
            GetSystemMetrics(small ? SM_CXSMICON : SM_CXICON),
            GetSystemMetrics(small ? SM_CYSMICON : SM_CYICON), LR_SHARED);
        if (icon) SendMessageW(window, WM_SETICON, small ? ICON_SMALL : ICON_BIG, reinterpret_cast<LPARAM>(icon));
    }
}
'''),encoding="utf-8")
    for name in ("launcher_ui.cpp","tool_window.cpp"):
        p=host/name
        text=p.read_text(encoding="utf-8")
        marker="glfwMakeContextCurrent(win);"
        assert text.count(marker)==1
        p.write_text(text.replace(marker,"UmaipoeNavigation::SetWindowIcons(glfwGetWin32Window(win));\n\t"+marker),encoding="utf-8")
