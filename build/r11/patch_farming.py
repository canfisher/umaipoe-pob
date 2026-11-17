from pathlib import Path
import shutil

def apply(root):
    host = Path(root) / 'host'
    source = Path(__file__).parent
    for name in ('umaipoe_farming.h', 'umaipoe_farming_panel.inc', 'farming_test.cpp'):
        shutil.copy2(source / name, host / name)
    path = host / 'atlas_planner.cpp'
    text = path.read_text(encoding='utf-8')
    text = text.replace('#include <vector>', '#include <vector>\n#include "umaipoe_farming.h"', 1)
    text = text.replace('\tvoid saveActive()', '#include "umaipoe_farming_panel.inc"\n\tvoid saveActive()', 1)
    text = text.replace('// --- points summary (pinned):', 'renderFarmingPanel();\n\t\t\t// --- points summary (pinned):', 1)
    path.write_text(text, encoding='utf-8')
    path = host / 'atlas_persist.h'
    text = path.read_text(encoding='utf-8')
    text = text.replace('\tstd::string notes;', '\tstd::string farming;\n\tstd::string notes;', 1)
    path.write_text(text, encoding='utf-8')
    path = host / 'atlas_persist.cpp'
    text = path.read_text(encoding='utf-8')
    text = text.replace('\te.notes = obj.value', '\te.farming = obj.contains("farming") && obj["farming"].is_object() ? obj["farming"].dump() : std::string();\n\te.notes = obj.value', 1)
    text = text.replace('\tif (!e.notes.empty())', '\tif (!e.farming.empty()) { auto f = ordered_json::parse(e.farming, nullptr, false); if (f.is_object()) obj["farming"] = f; }\n\tif (!e.notes.empty())', 1)
    start = text.index('static bool write_file_utf8(')
    end = text.index('\nstatic std::vector<int>', start)
    text = text[:start] + '''static bool write_file_utf8(const std::wstring& path, const std::string& content)
{
    const std::wstring temp = path + L".tmp-" + std::to_wstring(GetCurrentProcessId());
    HANDLE h = CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    DWORD written = 0;
    bool ok = (content.empty() || (WriteFile(h, content.data(), static_cast<DWORD>(content.size()), &written, nullptr)
        && written == content.size())) && FlushFileBuffers(h);
    CloseHandle(h);
    if (ok) {
        if (GetFileAttributesW(path.c_str()) != INVALID_FILE_ATTRIBUTES)
            ok = ReplaceFileW(path.c_str(), temp.c_str(), (path + L".bak").c_str(), 0, nullptr, nullptr) != 0;
        else ok = MoveFileExW(temp.c_str(), path.c_str(), MOVEFILE_WRITE_THROUGH) != 0;
    }
    if (!ok) DeleteFileW(temp.c_str());
    return ok;
}
''' + text[end:]
    path.write_text(text, encoding='utf-8')
