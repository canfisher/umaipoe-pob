from pathlib import Path
import json,sys,re,gzip,hashlib,shutil

root=Path(__file__).resolve().parents[2]
work=Path(__file__).parent
app=root/'outputs/pob330-r12/Umaipoe-PoB-r12'
data=app/'Data'
script=root/'work/pob330-r11-localization/release-repo/build/r11/localize-jewel-display.py'
sys.argv=[str(script),'--app',str(app)]
scope={'__file__':str(script)}
exec(script.read_text(encoding='utf-8').split('\nreport = {}')[0],scope)
base_translate=scope['translate']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
official={lang:{x['id']:x for group in read(work/f'trade-stats-{lang}.json')['result'] for x in group['entries']} for lang in ['ko','en']}
paired={v['text']:official['ko'][k]['text'] for k,v in official['en'].items() if k in official['ko'] and '#' in v['text']}
overrides={
'+0.4 metres to Melee Strike Range while at least 5 Enemies within 6 metres':'6미터 내 적이 5명 이상인 동안 근접 타격 범위 +0.4미터',
'Each Totem applies 1% increased Damage taken to Enemies within 3 metres':'토템 하나당 3미터 내 적이 받는 피해 1% 증가',
'Prefix':'접두어','Suffix':'접미어','Both':'접두어·접미어','Enchantment':'인챈트','Large':'대형','Medium':'중형','Small':'소형','Several sizes':'여러 크기','Small passives':'소형 패시브',
'Map modifiers':'지도 속성','Expedition logbook modifiers':'탐험 일지 속성','Flask modifiers':'플라스크 속성','Cluster jewel modifiers':'군 주얼 속성','Gem names':'젬 이름','Tattoos':'문신','Heist equipment modifiers':'강탈 장비 속성','Heist contracts':'강탈 계약','Vendor bases':'상점 장비 기반','Beasts':'야수','Magic affixes':'마법 속성 이름',
'Map Tier':'지도 등급','Item Quantity':'아이템 수량','Item Rarity':'아이템 희귀도','Monster Pack Size':'몬스터 무리 규모','Quality':'퀄리티','Item Level':'아이템 레벨','Sockets':'홈','Level':'레벨','Corrupted':'타락',
}
fallback=set()
def tr(s):
 if not isinstance(s,str):return s
 if s in overrides:return overrides[s]
 if s in paired:return paired[s]
 v=base_translate(s)
 if v==s and s.startswith('Added Small Passive Skills grant: '):v='추가된 소형 패시브 스킬이 부여: '+tr(s.split(': ',1)[1])
 if v==s and re.search('[A-Za-z]{3}',s):fallback.add(s)
 return v

tree=read(data/'passive_tree_poe1.json')
def patch_tree(x):
 if isinstance(x,dict):
  for en,ko in [('stats','statsZh'),('name','nameZh')]:
   if en in x and ko in x:x[ko]=[tr(s) for s in x[en]] if isinstance(x[en],list) else tr(x[en])
  for v in x.values():patch_tree(v)
 elif isinstance(x,list):
  for v in x:patch_tree(v)
patch_tree(tree);write(data/'passive_tree_poe1.json',tree)

for lang in ['en','ko']:
 records=[]
 for ident,entry in official[lang].items():
  kind=ident.split('.')[0]
  if kind not in ['explicit','implicit','crafted','fractured']:continue
  en=official['en'].get(ident)
  if not en or ident not in official['ko']:continue
  records.append({'ref':en['text'],'matchers':[{'string':entry['text']}],'trade':{'ids':{kind:[ident]}}})
 dest=data/'regex_stats/poe1'/('ko-KR' if lang=='ko' else 'en')/'stats.ndjson.gz'
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_bytes(gzip.compress(('\n'.join(json.dumps(x,ensure_ascii=False,separators=(',',':')) for x in records)+'\n').encode(),mtime=0))

regex=read(data/'regex_poe1.json')
for key,en in regex['labels']['en'].items():regex['labels']['zh'][key]=tr(en)
titles=['지도 속성','탐험 일지 속성','플라스크 속성','군 주얼 속성','젬 이름','문신','강탈 장비 속성','강탈 계약','상점 장비 기반','야수','마법 속성 이름']
def parallel(x):
 if isinstance(x,dict):
  pairs=[('en','zh'),('groupsEn','groups'),('titleEn','title')]+[(k,k[:-2]+'Zh') for k in x if k.endswith('En') and k[:-2]+'Zh' in x]
  for en,ko in pairs:
   if en in x and ko in x:
    x[ko]=[tr(v) for v in x[en]] if isinstance(x[en],list) else tr(x[en])
  if 'affixZh' in x:x['affixZh']=''
  for k,v in x.items():
   if k not in ['zh','hiddenZh','groups','title','affixZh']:parallel(v)
 elif isinstance(x,list):
  for v in x:parallel(v)
parallel(regex)
for page,title in zip(regex['pages'],titles):
 page['title']=title
 page['note']='조건을 고르면 검색식이 만들어집니다. 한국어 원문이 확인되지 않은 이름은 영문으로 표시됩니다. 실제 게임 복사문으로 일치 여부를 확인하세요.'
regex['source']='Official Korean/English trade stat text checked 2026-11-18; existing catalog translated against bundled Korean dictionary. Catalog additions require separate data validation.'
write(data/'regex_poe1.json',regex)
labels=read(data/'regex_labels_poe1.json');labels['labels']=regex['labels'];labels['source']=regex['source'];labels['note']='한국어 검색식용 표시 문구';write(data/'regex_labels_poe1.json',labels)
templates=read(data/'regex_templates.json')
template_text=[('고위험 지도 속성 제외','플라스크 효과 감소·막기·회복 제한 등 위험 속성을 제외합니다. 빌드에 맞춰 조정하세요.'),('반사·최대 저항 감소 제외','원소·물리 가시와 최대 저항 감소를 제외합니다.'),('상점 6연결','6연결 홈이 있는 아이템을 찾습니다.'),('상점 빨강·초록·파랑 연결','연결된 빨강·초록·파랑 홈을 찾습니다.'),('탐험 일지 위험 속성 제외','반사·재생 불가·최대 저항 감소를 제외합니다. 나머지 속성의 안전성을 보장하지 않습니다.'),('경로석 위험 속성 제외','PoE2 경로석용입니다. 빌드에 맞춰 조정하세요.'),('서판 보상 속성','PoE2 서판 보상 관련 속성 예시입니다.')]
for entry,(name,desc) in zip(templates['templates'],template_text):entry['name']['zh']=name;entry['desc']['zh']=desc
templates['source']='기존 검색 조건을 한국어 설명으로 정리한 예시';write(data/'regex_templates.json',templates)

base=read(work/'repoe-3.30/poe1-3.30.0.2.2/base_items.min.json')
items=read(data/'filter_items_zh.json')
for item in base.values():
 if item['release_state']=='released':items[item['name']]=tr(item['name'])
write(data/'filter_items_zh.json',items)
for name,records in [('scarabs_poe1.json','scarabs'),('astrolabes_poe1.json','astrolabes')]:
 d=read(data/name)
 for item in d[records]:
  if item['id'] in base:
   src=base[item['id']];item['en']=src['name'];item['zh']=tr(src['name'])
   item['descEn']=[src['properties']['description']] if src['properties'].get('description') else item.get('descEn',[])
  item['descZh']=[tr(v) for v in item.get('descEn',[])]
 for region in d.get('regions',[]):region['vaultZh']=tr(region['vaultEn'])
 d['sourceValidation']={'baseItemsVersion':'3.30.0.2.2','descriptionFallback':'prior source where current export has no effect description','numericMechanicsReverified':False}
 write(data/name,d)
metadata=read(data/'poe1/zh-rTW/item_metadata.json')
headers={'Item Class':'아이템 종류','Rarity':'아이템 희귀도','Quality':'퀄리티','Evasion Rating':'회피','Energy Shield':'에너지 보호막','Armour':'방어도','Requirements':'요구사항','Level':'레벨','Item Level':'아이템 레벨','Sockets':'홈','Map Tier':'지도 등급','Stack Size':'중첩 개수'}
values={'Normal':'일반','Magic':'마법','Rare':'희귀','Unique':'고유','Gem':'젬','Currency':'화폐','Divination Card':'점술 카드','Quest':'퀘스트','Unidentified':'미확인','Corrupted':'타락','Mirrored':'복제','Fractured Item':'분열된 아이템','Synthesised Item':'결합된 아이템','Split':'분할','Searing Exarch Item':'작열의 총주교 아이템','Eater of Worlds Item':'세계 포식자 아이템'}
enclasses=read(data/'item_classes_en.json');koclasses=read(data/'item_classes_zh.json')
values.update({v:koclasses[k] for k,v in enclasses.items() if k in koclasses})
for section,entries in metadata.items():
 if isinstance(entries,list):
  for entry in entries:
   if isinstance(entry,dict) and 'en' in entry:entry['zh']=headers.get(entry['en'],values.get(entry['en'],tr(entry['en'])))
for en,ko in headers.items():
 if not any(e['en']==en for e in metadata['headers']):metadata['headers'].append({'en':en,'zh':ko})
write(data/'poe1/ko-KR/item_metadata.json',metadata)
maps=read(data/'atlas_maps_poe1.json')
for entry in maps['maps']:
 item_name=tr(entry['enItem']);entry['zhItem']=item_name
 entry['zhArea']=item_name[:-3] if item_name.endswith(' 지도') else tr(entry['enArea'])
write(data/'atlas_maps_poe1.json',maps)
manifest={'version':'r12','passiveTree':'3_30','gameData':'3.30.0.2.2','statSource':'https://poe.kakaogames.com/api/trade/data/stats','statEntries':len(official['ko']),'untranslatedEnglish':sorted(fallback),'scope':'Korean menus and 3.30 tree; unresolved English catalog names remain explicit fallbacks.'}
write(app.parent/'tool-data-report.json',manifest)
print(json.dumps({'tree':tree.get('treeVersion'),'officialKoreanStats':len(official['ko']),'englishFallback':len(fallback)}))
