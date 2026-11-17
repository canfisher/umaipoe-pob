from pathlib import Path
import collections
import copy
import hashlib
import json
import re
import shutil
import argparse

workspace = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--app', type=Path, default=workspace / 'outputs/pob330-r11.1/Umaipoe-PoB-r11.1')
parser.add_argument('--report-dir', type=Path)
args = parser.parse_args()
output = args.report_dir or args.app.parent
data = args.app / 'Data'
backup = output / 'backups/before-jewel-display'
backup.mkdir(parents=True, exist_ok=True)
def clean(text):
    text = re.sub(r'\[([^]|]+)\|([^]]+)\]', r'\2', text)
    text = re.sub(r'\[([^]]+)\]', r'\1', text)
    return re.sub(r'[ \t]+', ' ', text.replace('\\n', '\n')).strip()


value = r'(?:[+-]?\([+-]?\d+(?:\.\d+)?-[+-]?\d+(?:\.\d+)?\)|[+-]?\d+(?:\.\d+)?|#)'
placeholder = r'\{(\d+)(?::([^}]*))?\}'
dictionaries = []
overrides = json.loads(Path(__file__).with_name('jewel-ko-overrides.json').read_text(encoding='utf-8'))
name_sources = json.loads((data / 'poe1/ko-KR/stats.json').read_text(encoding='utf-8-sig'))['entries']
for en, ko in overrides['names'].items():
    assert any(en in source and ko in translation for source, translation in name_sources.items()), en
for name in ('overrides', 'stats', 'passives', 'ui', 'items', 'uniques', 'gems', 'tags', 'monsters'):
    entries = ({**overrides['names'], **overrides['ui_labels'], **overrides['stat_templates']} if name == 'overrides'
               else json.loads((data / f'poe1/ko-KR/{name}.json').read_text(encoding='utf-8-sig'))['entries'])
    exact, patterns = {}, collections.defaultdict(list)
    for en, ko in entries.items():
        if not isinstance(ko, str) or not re.search('[가-힣]', ko):
            continue
        en, ko = clean(en), clean(ko)
        pairs = [(en, ko)]
        if '\n' in en and len(en.splitlines()) == len(ko.splitlines()):
            pairs += list(zip(en.splitlines(), ko.splitlines()))
        for en, ko in pairs:
            exact[en.casefold()] = ko
            fields = [m[0] for m in re.findall(placeholder, en)]
            if not fields:
                continue
            expression, offset = '', 0
            for token in re.finditer(placeholder, en):
                expression += re.escape(en[offset:token.start()]) + '(' + value + ')'
                offset = token.end()
            expression += re.escape(en[offset:])
            key = re.sub(value, '#', re.sub(placeholder, '#', en)).casefold()
            patterns[key].append((re.compile('^' + expression + '$', re.I), fields, ko))
    dictionaries.append((name, exact, patterns))

missing = set()
provenance = {}


def translate(text):
    plain = clean(text)
    if re.fullmatch(r'Notable \d+', plain):
        provenance[plain] = 'internal-placeholder-label'
        return plain.replace('Notable', '주요 패시브')
    key = re.sub(value, '#', plain).casefold()
    for name, exact, patterns in dictionaries:
        if plain.casefold() in exact and not re.search(r'\{[^}]*\}', exact[plain.casefold()]):
            provenance[plain] = name + ':exact'
            return exact[plain.casefold()]
        for pattern, fields, ko in patterns.get(key, []):
            match = pattern.fullmatch(plain)
            if not match:
                continue
            values = dict(zip(fields, match.groups()))
            if any(values[field] != matched for field, matched in zip(fields, match.groups())):
                continue
            def substitute(token):
                result = values.get(token[1], token[0])
                if token[2] and '+' in token[2] and not result.startswith(('+', '-', '#')):
                    result = '+' + result
                return result
            result = re.sub(placeholder, substitute, ko)
            if re.search(r'\{[^}]*\}', result):
                continue
            provenance[plain] = name + ':template'
            return result
    if '\n' in plain:
        return '\n'.join(translate(line) for line in plain.splitlines())
    missing.add(plain)
    return plain


localized_keys = {'nameZh', 'dnZh', 'sdZh', 'statsZh', 'nameAliases'}


def structural(value):
    if isinstance(value, dict):
        return {k: structural(v) for k, v in value.items() if k not in localized_keys}
    if isinstance(value, list):
        return [structural(v) for v in value]
    return value


def localize(value):
    if isinstance(value, dict):
        for english, korean in [('name', 'nameZh'), ('dn', 'dnZh'), ('sd', 'sdZh'), ('stats', 'statsZh')]:
            if korean not in value or english not in value:
                continue
            source = value[english]
            if isinstance(source, str):
                value[korean] = translate(source)
            elif isinstance(source, list) and all(isinstance(s, str) for s in source):
                value[korean] = [translate(s) for s in source]
        for key, item in value.items():
            if key not in localized_keys:
                localize(item)
    elif isinstance(value, list):
        for item in value:
            localize(item)


report = {}
for name in ['timeless_jewels.json', 'passive_tree_poe1.json']:
    path = data / name
    original = json.loads(path.read_text(encoding='utf-8-sig'))
    modified = copy.deepcopy(original)
    if name == 'timeless_jewels.json':
        reference = json.loads((backup / name).read_text(encoding='utf-8-sig'))
        aliases = {(kind, leader['id']): leader['nameZh'] for kind, leaders in reference['conquerors'].items() for leader in leaders}
        for kind, leaders in modified['conquerors'].items():
            for leader in leaders:
                old_name = aliases[(kind, leader['id'])]
                leader['nameAliases'] = [old_name] if old_name and old_name != translate(leader['name']) else []
    localize(modified)
    assert structural(original) == structural(modified)
    if not (backup / name).exists():
        shutil.copy2(path, backup / name)
    path.write_text(json.dumps(modified, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    report[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'calculation_data_unchanged': True,
                    'version': original.get('version'), 'treeVersion': original.get('treeVersion')}
report['unmatched_display_text_english_fallback'] = sorted(missing)
report['source'] = 'Bundled ko-KR dictionaries; only display fields changed; numeric values preserved.'
report['translation_provenance'] = provenance
(output / 'jewel-display-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'files': {k: v for k, v in report.items() if k.endswith('.json')}, 'unmatched_count': len(missing)}, ensure_ascii=True))
