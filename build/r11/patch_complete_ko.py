from pathlib import Path
import json,re

def apply(root):
    from patch_branding import function_body
    host=Path(root)/'host'
    mapping=json.loads(Path(__file__).with_name('complete-ko.json').read_text(encoding='utf-8'))
    token=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|[\x27](?:[^\x27\\]|\\.)*[\x27]|(?:u8|L)?R"(?P<delim>[^ ()\\\t\r\n]{0,16})\([\s\S]*?\)(?P=delim)"|(?P<prefix>u8|L)?"(?P<body>(?:[^"\\]|\\.)*)"')
    changed={}
    for path in host.glob('*'):
        if path.suffix not in ('.cpp','.h') or 'fixture' in path.name or 'selftest' in path.name: continue
        count=[0]
        def replace(m):
            source=m.group('body')
            if source not in mapping: return m.group()
            target=mapping[source]
            fmt=r'%(?:[-+0 #]*\d*(?:\.\d+)?[hlzjtL]*[a-zA-Z]|%)'
            assert re.findall(fmt,source)==re.findall(fmt,target),(path.name,source,target)
            count[0]+=1
            return (m.group('prefix') or '')+'"'+target+'"'
        text=token.sub(replace,path.read_text(encoding='utf-8-sig'))
        if count[0]: path.write_text(text,encoding='utf-8');changed[path.name]=count[0]
    p=host/'launcher_config.cpp';text=p.read_text(encoding='utf-8')
    text=text.replace('L"NotoSansTC-Regular.ttf"','L"NotoSansKR-Regular.ttf"')
    text=text.replace('if (c.locale.empty()) c.locale = L"zh-rTW";','c.locale = L"ko-KR";')
    p.write_text(text,encoding='utf-8')
    p=host/'launcher_ui.cpp';text=p.read_text(encoding='utf-8')
    text=text.replace('작업을 저장하고 종료한 뒤 다시 실행하면 적용됩니다.', '실행할 때 먼저 새 버전을 확인하고 적용한 뒤 PoB를 엽니다. 연결에 실패하면 설치된 정상 버전으로 실행합니다.')
    p.write_text(text,encoding='utf-8')
    p=host/'passive_tree_update.cpp';text=p.read_text(encoding='utf-8')
    for signature in ['void PassiveTreeUpdater::RequestCheck(', 'void PassiveTreeUpdater::StartUpdate(']:
        text=function_body(text,signature,'    setPhase(PassiveUpdatePhase::UpToDate, u8"트리와 한국어 자료는 Umaipoe-PoB.exe 실행 시 함께 업데이트됩니다.");')
    text=function_body(text,'int RunPassiveTreeUpdateCli(', '    printf("Use Umaipoe-PoB.exe for signed Korean data updates.\\n");\n    return 3;')
    p.write_text(text,encoding='utf-8')
    p=host/'host_main.cpp';text=p.read_text(encoding='utf-8')
    text=text.replace('ensure(L"POB_LOCALE", L"Locale", L"zh-rTW");','SetEnvironmentVariableW(L"POB_LOCALE", L"ko-KR");')
    p.write_text(text,encoding='utf-8')
    p=host/'passive_import.cpp';text=p.read_text(encoding='utf-8')
    text=text.replace('L"Data\\\\poe1\\\\zh-rTW\\\\"','L"Data\\\\poe1\\\\ko-KR\\\\"')
    p.write_text(text,encoding='utf-8')
    p=host/'regex_itemmods.cpp';text=p.read_text(encoding='utf-8').replace('"cmn-Hant" : "en"','"ko-KR" : "en"')
    p.write_text(text,encoding='utf-8')
    p=host/'regex_tool_ui.cpp';text=p.read_text(encoding='utf-8').replace('cmn-Hant','ko-KR')
    p.write_text(text,encoding='utf-8')
    p=host/'timeless_jewel_ui.cpp';text=p.read_text(encoding='utf-8')
    text=text.replace('ptUpdater.RequestCheck(false);','// Passive data is released together with the verified Korean package.')
    p.write_text(text,encoding='utf-8')
    (Path(root)/'complete-korean-ui-report.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Additional Korean UI strings:',sum(changed.values()))
