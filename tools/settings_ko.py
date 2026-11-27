import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


UI = Path('Data/poe1/ko-KR/ui.json')
ENGINE = Path('PoE1-3.30')
LABELS = {
    'Show All Configurations': '모든 설정 표시',
    'Hide Ineligible Configurations': '해당 없는 설정 숨기기',
    'Act 5 (-30%)': '5장 (-30%)',
    'Act 10 (-60%)': '10장 (-60%)',
    'Do your minions have Onslaught?': '소환수가 맹공을 가지고 있습니까?',
    'Do your minions have Unholy Might?': '소환수가 불경한 힘을 가지고 있습니까?',
    'Do you have Chaotic Might?': '혼돈의 완력을 가지고 있습니까?',
    'Do your minions have Chaotic Might?': '소환수가 혼돈의 완력을 가지고 있습니까?',
    'Mana Burn Stacks:': '마나 연소 중첩:',
    'Have you Hit with a Spell Recently?': '최근 주문으로 명중시켰습니까?',
    'Have your Totems Hit Recently?': '최근 토템이 명중시켰습니까?',
    'Have your Totems Hit with a Spell Recently?': '최근 토템이 주문으로 명중시켰습니까?',
    '# of Mana spent Recently:': '최근 소모한 ^x7070FF마나^7:',
    'Include in Mana spent Recently?': '최근 소모한 ^x7070FF마나^7에 포함합니까?',
    '# of Life spent Recently:': '최근 소모한 ^xE05030생명력^7:',
    '# of Warcries Used Recently:': '최근 사용한 함성 횟수:',
    'Is the enemy Burning?': '적이 ^xB97123화상^7을 받고 있습니까?',
    'Is the enemy Ignited?': '적이 ^xB97123점화^7 상태입니까?',
    'Is the enemy Scorched?': '적이 ^xB97123그을림^7 상태입니까?',
    'Is the enemy on Scorched Ground?': '적이 ^xB97123그을린 지대^7에 있습니까?',
    'Is the enemy Chilled?': '적이 ^x3F6DB3냉각^7 상태입니까?',
    'Seconds of chill on enemy?': '적이 냉각된 시간(초):',
    'Effect of Chill:': '^x3F6DB3냉각^7 효과:',
    'Is the enemy Frozen?': '적이 ^x3F6DB3동결^7 상태입니까?',
    'Is the enemy Shocked?': '적이 ^xADAA47감전^7 상태입니까?',
    'Is the enemy on Shocked Ground?': '적이 ^xADAA47감전 지대^7에 있습니까?',
    'Effect of Shock:': '^xADAA47감전^7 효과:',
    'Is the enemy in a Chilling area?': '적이 ^x3F6DB3냉각 지대^7에 있습니까?',
    'Enemy Base Evasion:': '적 기본 ^x33FF77회피^7:',
    'Enemy Skill Physical Overwhelm:': '적 스킬의 물리 피해 감소 무시:',
    'This also implies that the enemy is Burning.': '적이 ^xB97123화상^7을 받고 있는 것으로도 계산합니다.',
    'This will enable the Chaotic Might buff.\n(Grants 30% of Physical Damage as Extra Chaos Damage)':
        '혼돈의 완력을 적용합니다.\n(물리 피해의 30%를 추가 ^xD02090카오스^7 피해로 획득)',
    'This will enable the Chaotic Might buff on your minions.\n(Grants 30% of Physical Damage as Extra Chaos Damage)':
        '소환수에게 혼돈의 완력을 적용합니다.\n(물리 피해의 30%를 추가 ^xD02090카오스^7 피해로 획득)',
    'Mana Burn Applies a 1% of mana degen per stack\nThis also applies Weeping Wounds if the Keystone is Allocated':
        '마나 연소 중첩당 1초마다 마나 최대치의 1%를 잃습니다.\n관련 핵심노드가 할당되어 있으면 진물 나는 상처도 적용합니다.',
}

for english, korean, color in (
    ('Lightning', '번개', '^xADAA47'), ('Cold', '냉기', '^x3F6DB3'),
    ('Fire', '화염', '^xB97123'), ('Chaos', '카오스', '^xD02090'),
):
    element = color + korean + '^7'
    LABELS[f'Enemy {english} Resistance:'] = f'적 {element} 저항:'
    LABELS[f'Enemy Skill {english} Damage:'] = f'적 스킬의 {element} 피해:'
    if english != 'Chaos':
        LABELS[f'Enemy Skill {english} Pen:'] = f'적 스킬의 {element} 저항 관통:'
        LABELS[f'Is the enemy Exposed to {english}?'] = f'적이 {element} 노출 상태입니까?'


def edit_text(raw, replacements):
    original = raw.decode('utf-8')
    updated = original
    line_end = '\r\n' if '\r\n' in original else '\n'
    for old, new in replacements.items():
        old, new = (text.replace('\n', line_end) for text in (old, new))
        if old not in updated and new not in updated:
            raise ValueError(f'Text missing: {old}')
        updated = updated.replace(old, new)
    return updated.encode('utf-8')


def prepare(root):
    dictionary = json.loads((root / UI).read_bytes())
    entries = dictionary['entries']
    entries.update(LABELS)

    config = ENGINE / 'Modules/ConfigOptions.lua'
    tab = ENGINE / 'Classes/ConfigTab.lua'
    stats = ENGINE / 'Modules/BuildDisplayStats.lua'
    launch = ENGINE / 'Launch.lua'
    launch_data = (root / launch).read_bytes()
    version = re.search(rb'APP_NAME = "[^"\r\n]+ (r[\d.]+) \(([\d.]+)\)"', launch_data)
    if not version:
        raise ValueError('Release version missing from program title')
    release, game = (part.decode('ascii') for part in version.groups())
    launch_data = edit_text(launch_data, {
        'self.customDataVersion = "3.30-r13.4"': f'self.customDataVersion = "{game}-{release}"',
        'self.customName = "우마이 한글 PoB r13.4"': f'self.customName = "우마이 한글 PoB {release}"',
        'self.customGameVersion = "3.30 · r13.4"': f'self.customGameVersion = "{game} · {release}"',
    })
    return {
        UI: json.dumps(dictionary, ensure_ascii=False, separators=(',', ':')).encode('utf-8'),
        config: edit_text((root / config).read_bytes(), {
            'Sacrament 사용 직전 생명력': '성체 사용 직전 생명력',
            '활성 Sacrament의 1회 사용 손실·보복 개방 확률. 비우면 가용 생명력이 찬 상태. 현재 생명력 기준 계산이며 플라스크 효과로 사용 시 손실을 증폭하지 않습니다.':
                '공포의 마녀의 성체 사용 시 생명력 손실과 보복 스킬 사용 가능 확률을 계산합니다. 비워 두면 점유되지 않은 생명력이 가득 찬 상태로 계산합니다. 플라스크 효과는 생명력 손실량에 적용하지 않습니다.',
        }),
        tab: edit_text((root / tab).read_bytes(), {
            'end)\n\n\tself.controls.addModBtn = new("ButtonControl")':
                'end)\n\tself.controls.titleEdit.inactiveText = function(title)\n\t\treturn title == "Default" and "기본" or title\n\tend\n\n\tself.controls.addModBtn = new("ButtonControl")',
            '{6, 0, 222, 18}, blockData.title or ""': '{6, 0, 200, 18}, blockData.title or ""',
            '{6, 0, 58, 18}, "^7Add Mod"': '{6, 0, 80, 18}, "^7Add Mod"',
        }),
        stats: edit_text((root / stats).read_bytes(), {
            'Sacrament 생명력 손실': '성체 생명력 손실',
            'Sacrament 잔여 생명력': '성체 사용 후 생명력',
            'Sacrament 보복 확률': '성체 보복 스킬 사용 가능 확률',
        }),
        launch: launch_data,
    }


def apply(root, backup_root):
    changed = {file: data for file, data in prepare(root).items() if (root / file).read_bytes() != data}
    if not changed:
        print('Current files already match')
        return
    backup = backup_root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    for file in changed:
        original = backup / file
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / file, original)

    written = []
    try:
        for file, data in changed.items():
            target = root / file
            temporary = target.with_name(target.name + '.settings-ko.tmp')
            try:
                temporary.write_bytes(data)
                os.replace(temporary, target)
                written.append(file)
            finally:
                temporary.unlink(missing_ok=True)
    except OSError:
        for file in reversed(written):
            shutil.copy2(backup / file, root / file)
        raise
    print(f'Applied {len(LABELS)} Korean strings across {len(changed)} files. Backup: {backup}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('backup_root', type=Path)
    args = parser.parse_args()
    apply(args.root, args.backup_root)
