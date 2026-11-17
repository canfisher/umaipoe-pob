import json
from pathlib import Path

UI = dict(line.split(' => ', 1) for line in '''Tree => 패시브
Build => 빌드
Current build => 현재 빌드
Keep => 유지
Open => 열기
Import => 가져오기
Import Tree => 패시브 가져오기
Delete => 삭제
Clear => 지우기
End => 종료
Final => 최종
Current => 현재
State: => 상태:
Mode => 모드
Maximum => 최대
Allocated => 할당됨
Don't Save => 저장 안 함
Ignore => 무시
Accuracy => 명중
Brittle => 허약
Elusive => 도피
Warden => 워든
Shield => 방패
Corpse Life => 시체 생명력
Corpse Level => 시체 레벨
Poison => 중독
Poison DPS: => 중독 DPS:
# of Poison on enemy: => 적에게 적용된 중독 중첩 수:
# of Poison on You: => 자신에게 적용된 중독 중첩 수:
# of Poisons applied Recently: => 최근에 유발한 중독 횟수:
# of Spider's Web Stacks: => 거미줄 중첩 수:
# of Frenzy Charges (if not maximum): => 격분 충전 개수(최대가 아닐 때):
# of Power Charges (if not maximum): => 권능 충전 개수(최대가 아닐 때):
Sap Effect => 활력 감소 효과
Attack Dodge Chance => 공격 완벽회피 확률
Spell Dodge Chance => 주문 완벽회피 확률
Spell Suppression => 주문 피해 억제
Unlucky => 불운
Very Unlucky => 매우 불운
Crit Multiplier => 치명타 피해 배율
Effective Crit Chance => 유효 치명타 확률
Evasion rating => 회피
Cast Time => 시전 시간
Attack/Cast Rate => 공격/시전 속도
Totem Placement Time => 토템 설치 시간
Trap Throwing Time => 덫 투척 시간
Hit Rate => 초당 적중 횟수
Hit Chance => 명중 확률
Hit DPS => 적중 DPS
Average Hit => 평균 적중 피해
Average Dmg. inc. Ignite => 점화 포함 평균 피해
Combined DPS => 합산 DPS
Total DPS inc. Ignite => 점화 포함 총 DPS
Total DPS inc. Poison => 중독 포함 총 DPS
Total Damage per Poison => 중독 1중첩당 총 피해
Include in Full DPS: => 전체 DPS에 포함:
Damage mitigated: => 완화된 피해:
Enemy Stats => 적 능력치
Enemy Skill Physical Damage: => 적 스킬의 물리 피해:
Chaos Res. Over Max => 최대치를 초과한 카오스 저항
Cold Res. Over Max => 최대치를 초과한 냉기 저항
Fire Res. Over Max => 최대치를 초과한 화염 저항
Lightning Res. Over Max => 최대치를 초과한 번개 저항
Chaos Resist => 카오스 저항
Recharge rate: => 초당 재충전량:
Rate per instance: => 흡수 1회당 초당 회복량:
ES Leech/Gain per Hit => 적중당 에너지 보호막 흡수/획득량
ES Leech/On Hit Rate => 초당 에너지 보호막 흡수/적중 시 획득량
Life Leech/Gain per Hit => 적중당 생명력 흡수/획득량
Life Leech/On Hit Rate => 초당 생명력 흡수/적중 시 획득량
Mana Leech/Gain per Hit => 적중당 마나 흡수/획득량
Mana Leech/On Hit Rate => 초당 마나 흡수/적중 시 획득량
Current attributes => 현재 능력치
Custom Modifiers => 사용자 지정 속성 부여
Crafting Bench => 제작대
Base: => 기본 유형:
Crafted => 제작 속성 부여
Keystone => 핵심노드
Notable => 주요 패시브
Jewel sockets => 주얼 홈
Jewel Socket: => 주얼 홈:
Socket Group: => 젬 연결 그룹:
^x7F7F7FSockets: => ^x7F7F7F홈:
Link => 연결
Herald => 전령
Spectre => 망령
Consumed a corpse Recently? => 최근에 시체를 소모했습니까?
Have your Skills Crit Recently? => 최근에 스킬로 치명타를 명중시켰습니까?
Have you Blocked a Spell Recently? => 최근에 주문을 막았습니까?
Have you Blocked an Attack Recently? => 최근에 공격을 막았습니까?
Have you Blocked Recently? => 최근에 공격 또는 주문을 막았습니까?
This also implies that you have Blocked Recently. => 이 설정은 최근에 공격 또는 주문을 막은 상태도 포함합니다.
Do you have Soul Gain Prevention? => 영혼 획득 방지 상태입니까?
Do you have Vaal Arc's Lucky Buff? => 바알 연쇄 번개의 행운 버프가 있습니까?
Cannot fork => 분기 불가
Cannot chain => 연쇄 불가
Cannot pierce => 관통 불가
% increased effect of map mods => 지도 속성 부여 효과 증가(%)
Ctrl + Click to enable/disable socket groups. => Ctrl+클릭하여 젬 연결 그룹을 활성화하거나 비활성화합니다.
Are you sure you want to delete all socket groups in this build? => 이 빌드의 모든 젬 연결 그룹을 삭제하시겠습니까?
Click to level up all gems that you haven't locked => 잠그지 않은 모든 젬의 레벨을 올립니다.
This will allow the skill to benefit from modifiers on the item that affect socketed gems. => 장착된 젬에 영향을 주는 아이템 속성 부여가 이 스킬에 적용됩니다.
Tip: Right click this socket to go to the items page and choose the jewel for this socket. => 팁: 이 홈을 우클릭하면 아이템 화면에서 장착할 주얼을 선택할 수 있습니다.
(A Hit that removes at least 15% of Maximum Life is a Savage Hit) => (한 번의 피격으로 생명력 최대치의 15% 이상을 잃으면 야만적인 타격입니다)
'''.strip().splitlines())

UI.update({
    'Shadow': '쉐도우', 'SHADOW': '쉐도우',
    'From': '출처', 'Local': '아이템 자체', 'Stat': '능력치',
    'Small': '소형', 'Medium': '중형', 'Spawn': '생성', 'Kill': '처치',
    'Reset Tree/Tattoos': '패시브·문신 초기화', 'Version:': '버전:',
    'Do you want to save them before exiting?': '종료하기 전에 변경사항을 저장하시겠습니까?',
})
UI.update(dict(line.split(' => ',1) for line in """Any Loadout => 모든 구성
Del Unused => 미사용 삭제
Del All => 전체 삭제
Add Mod => 속성 부여 추가
Add Mod Group => 속성 부여 그룹 추가
Anoint 2... => 성유 붓기 2...
Anoint 3... => 성유 붓기 3...
Anoint 4... => 성유 붓기 4...
Change Enchantment 2... => 인챈트 변경 2...
Change Enchantment... => 인챈트 변경...
Compare with: => 비교 대상:
Config set: => 설정 세트:
Copy + Convert => 복사 후 변환
Copy tree => 패시브 복사
Devotion modifiers: => 헌신 속성 부여:
Enter name for this loadout: => 이 구성의 이름을 입력하세요:
Enter passive tree link: => 패시브 스킬 트리 주소를 입력하세요:
Expanded mode => 확장 모드
Imbued Support: => 부여된 보조 젬:
Import as comparison => 비교용으로 가져오기
Import from Folder => 폴더에서 가져오기
Missing discriminator e.g. #1234 => 계정 식별번호가 없습니다(예: #1234)
Modifier sorting: => 속성 부여 정렬:
New Loadout => 새 구성
Node Distance: => 패시브 거리:
Open Trade URL => 거래소 검색 열기
Optimise Sockets => 주얼 홈 최적화
Overlay comparison => 겹쳐서 비교
Passive tree link: => 패시브 스킬 트리 주소:
Re-import Current => 현재 캐릭터 다시 가져오기
Remove All Tattoos => 모든 문신 제거
Required ascendancy outcome: => 필요한 전직 효과:
Reset Tree => 패시브 초기화
Show Color Codes => 색상 코드 표시
Show Legacy Tattoos: => 기존 버전 문신 표시:
Show legacy gems: => 기존 버전 젬 표시:
Show only differences => 차이점만 표시
Shrink with PoEURL => PoEURL로 주소 줄이기
Skill gems: => 스킬 젬:
Socket Jewel: => 주얼 장착:
Support gems: => 보조 젬:
Tattoo Count: => 문신 개수:
This Items Implicits Cannot Be Changed => 이 아이템의 고정 속성은 변경할 수 없습니다
Total Minimum Weight: => 최소 가중치 합계:
Tree set: => 패시브 세트:
Warcry Skills => 함성 스킬
""".strip().splitlines()))
UI.update({key+':':value+':' for key,value in list(UI.items()) if not key.endswith((':','?','.'))})

# UI entries are also present in other dictionaries loaded after ui.json.
SHARED = {k: UI[k] for k in ['Accuracy', 'Brittle', 'Elusive', 'Warden', 'Corpse Life', 'Corpse Level']}
LAUNCHER = {
    'Tree backdrop': '패시브 배경',
    'Automatic checks run at most once a day, and only at startup. Click to check right now.': 'Umaipoe-PoB.exe를 실행할 때마다 새 버전을 확인합니다. 열린 PoB는 저장 후 종료하고 다시 실행하면 적용됩니다.',
}

def patch_dictionary(name, content):
    if not name.startswith('Data/') or '/ko-KR/' not in name or not name.endswith('.json'):
        return content, []
    doc = json.loads(content)
    if name == 'Data/poe1/ko-KR/meta.json':
        doc['load_order'] = list(dict.fromkeys(doc['load_order'] + ['ui_terminology.json']))
        doc['source_lookup'] = True
        doc['source_dicts'] = list(dict.fromkeys(doc.get('source_dicts', []) + ['ascendancy_by_id.json']))
        return json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode(), []
    entries = doc.get('entries', {})
    overrides = LAUNCHER if name == 'Data/launcher/ko-KR/launcher.json' else UI if name == 'Data/poe1/ko-KR/ui.json' else SHARED
    changes = []
    for key, value in overrides.items():
        if key in entries and entries[key] != value:
            changes.append({'file': name, 'key': key, 'before': entries[key], 'after': value})
            entries[key] = value
    return (json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode(), changes) if changes else (content, [])

if __name__ == '__main__':
    import sys
    root = Path(sys.argv[1])
    changes = []
    for file in (root/'Data').rglob('*.json'):
        data, edits = patch_dictionary(file.relative_to(root).as_posix(), file.read_bytes())
        if edits:
            file.write_bytes(data)
            changes.extend(edits)
    print(json.dumps(changes, ensure_ascii=False, indent=2))
