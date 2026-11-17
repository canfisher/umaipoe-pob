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
text = '#include "umaipoe_support.h"\n' + text
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
