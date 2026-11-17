from pathlib import Path


def apply(root):
    host = Path(root) / 'host'
    path = host / 'timeless_jewel.h'
    text = path.read_text(encoding='utf-8')
    needle = '\tstd::string nameZh;  // "" -> fall back to name'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + '\n\tstd::vector<std::string> aliases;')
    text += '\nint RunTimelessKoreanSelfTest(const std::wstring& exeDir);\n'
    path.write_text(text, encoding='utf-8')
    path = host / 'timeless_jewel.cpp'
    text = path.read_text(encoding='utf-8')
    text = text.replace('q.nameZh = c.value("nameZh", std::string());',
                        'q.nameZh = c.value("nameZh", std::string());\n\t\t\t\t\tq.aliases = c.value("nameAliases", std::vector<std::string>{});')
    marker = '\t// seed = largest number on the line naming the conqueror'
    assert text.count(marker) == 1
    text = text.replace(marker, '''    if (!out.jewelType) {
        for (const auto& family : ds.conquerors) {
            for (int i = 0; i < (int)family.second.size(); ++i) {
                for (const auto& alias : family.second[i].aliases) {
                    const size_t at = alias.empty() ? std::string::npos : text.find(alias);
                    if (at != std::string::npos) {
                        out.jewelType = family.first;
                        out.conqIndex = i;
                        namePos = at;
                    }
                }
            }
        }
    }
''' + marker)
    text += '\n' + (Path(__file__).parent / 'jewel-ko-selftest.inc').read_text(encoding='utf-8')
    path.write_text(text, encoding='utf-8')
    path = host / 'host_main.cpp'
    text = path.read_text(encoding='utf-8')
    marker = '\tif (arg1 == L"--tj-selftest") {'
    assert text.count(marker) == 1
    text = text.replace(marker, '\tif (arg1 == L"--tj-ko-selftest") return RunTimelessKoreanSelfTest(dir);\n' + marker)
    path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    import sys
    apply(Path(sys.argv[1]))
