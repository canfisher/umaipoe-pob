from pathlib import Path
import json
import re
import sys

root = Path(sys.argv[1])
host = root / 'host'
source = host / 'launcher_ui.cpp'
text = source.read_text(encoding='utf-8-sig')
first = text.index('\t\t\t\t// Ours, not the game\'s:')
last = text.index('\n\t\t\t\tImGui::PopFont();', first)
text = text[:first] + '\t\t\t\tif (c == kLinkColumnCount - 1) UmaipoeSupportLink(exeDir);\n' + text[last:]
first = text.index('\t\t\tif (PobUi::Button(S.discord,')
last = text.index('\n\t\t\t// The attribution lines', first)
text = text[:first] + '\t\t\tUmaipoeSupportLink(exeDir);\n' + text[last:]
text = text.replace('#include <vector>', '#include <vector>\n#include "umaipoe_support.h"', 1)
assert 'https://discord.gg/6VamPQb8nC' not in text
assert 'https://hsiung-shao.github.io/support/' not in text
source.write_text(text, encoding='utf-8')

translations = json.loads((Path(__file__).parent / 'tool-ko.json').read_text(encoding='utf-8'))
token = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|[\x27](?:[^\x27\\]|\\.)*[\x27]|(?:u8|L)?R"(?P<delim>[^ ()\\\t\r\n]{0,16})\([\s\S]*?\)(?P=delim)"|(?P<prefix>u8|L)?"(?P<body>(?:[^"\\]|\\.)*)"')
changes = {}
for path in host.glob('*'):
    if path.suffix not in ('.cpp', '.h') or 'selftest' in path.name or path.name == 'launcher_strings.h':
        continue
    text = path.read_text(encoding='utf-8-sig')
    count = [0]
    def replace(match):
        source = match.group('body')
        if source not in translations:
            return match.group()
        target = translations[source]
        if re.findall(r'%(?:[-+0 #]*\d*(?:\.\d+)?[hlzjtL]*[a-zA-Z]|%)', source) != re.findall(r'%(?:[-+0 #]*\d*(?:\.\d+)?[hlzjtL]*[a-zA-Z]|%)', target):
            raise ValueError('Format specifiers changed: ' + source)
        count[0] += 1
        return (match.group('prefix') or '') + '"' + target + '"'
    text = token.sub(replace, text)
    if count[0]:
        path.write_text(text, encoding='utf-8')
        changes[path.name] = count[0]

(host / 'umaipoe_support.h').write_text((Path(__file__).parent / 'umaipoe_support.h').read_text(encoding='utf-8'), encoding='utf-8')
(root / 'localization-report.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(changes, ensure_ascii=False))
from patch_farming import apply
apply(root)
from patch_branding import apply as apply_branding
apply_branding(root)
ui_audit = {}
for name in ['atlas_planner.cpp', 'filter_editor.cpp', 'regex_tool_ui.cpp', 'timeless_jewel_ui.cpp', 'warehouse_ui.cpp']:
    untranslated = sorted({m.group('body') for m in token.finditer((host / name).read_text(encoding='utf-8'))
        if m.group('body') is not None and re.search(r'[\u4e00-\u9fff]', m.group('body'))})
    permitted = {'反射', '腐化的屍體'} if name == 'regex_tool_ui.cpp' else set()
    assert not set(untranslated) - permitted, (name, untranslated)
    ui_audit[name] = {'untranslated_ui': [], 'preserved_search_fixtures': untranslated}
(root / 'korean-ui-audit.json').write_text(json.dumps(ui_audit, ensure_ascii=False, indent=2), encoding='utf-8')
