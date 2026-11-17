from pathlib import Path
import hashlib,json,subprocess,zipfile
from terminology import patch_dictionary,UI

root=Path(__file__).resolve().parents[2]
old=root/'outputs/pob330-r12.1';out=root/'outputs/pob330-r12.2';out.mkdir(exist_ok=True)
notes="""우마이 한글 PoB r12.2 — 게임 용어 및 업데이트 대기 화면 수정

- 빌드·가져오기·유지·상태·종료 메뉴의 잘못된 직역을 수정했습니다.
- 워든·저거넛·방패·허약·도피·명중·시체 생명력·주문 피해 억제 등 용어를 바로잡았습니다.
- 젬과 주얼, 홈과 젬 연결 그룹을 구분하고 시전/토템 설치/덫 투척 시간 표시를 수정했습니다.
- 독 중첩 수를 적의 수로 표시하던 설명, 최대치를 초과한 저항, 흡수/적중 회복량 설명을 수정했습니다.
- 업데이트 정보 확인은 전체 통신 기준 최대 10초로 제한합니다. 통신 실패 시 설치된 정상 버전으로 실행합니다.
- 기존 설치가 있으면 '이번 확인 건너뛰기'로 다운로드를 취소하고 시작할 수 있습니다.
- 다운로드한 용량과 설치·실행 단계를 표시합니다. PoB가 시작되면 업데이트 창은 즉시 숨겨집니다.
- 새 버전의 계산·저장 검증과 실패 복구는 유지됩니다. PoB를 닫으면 숨겨진 실행기도 종료됩니다.
- Umaipoe-PoB.exe를 다시 실행하면 자동 적용됩니다. 기존 빌드·설정과 이전 버전은 보존됩니다.
- 이번 변경은 표시 사전과 실행기 수정입니다. 게임 계산 데이터는 r12.1과 같으며 모든 게임 상황의 실측 검증을 뜻하지 않습니다.
"""
for name in ['release-notes.md','패치노트.txt']:(out/name).write_text(notes,encoding='utf-8')
target=out/'Umaipoe-PoB-r12.2.zip';assert not target.exists()
changes=[];manifest={}
launcher=out/'Umaipoe-PoB.exe'
launcher_payload={'schema':1,'sequence':100007,'minLauncher':1,'launcherVersion':4,'kind':'launcher','version':'r12.2','url':'https://github.com/canfisher/umaipoe-pob/releases/download/r12.2/Umaipoe-PoB.exe','sha256':hashlib.sha256(launcher.read_bytes()).hexdigest(),'bytes':launcher.stat().st_size}
(out/'launcher-payload.json').write_text(json.dumps(launcher_payload,separators=(',',':')),encoding='utf-8')
subprocess.run([str(root/'work/pob-release-cli/Manifest.exe'),'sign',str(out/'launcher.json'),str(out/'launcher-payload.json')],check=True)
with zipfile.ZipFile(old/'Umaipoe-PoB-r12.1.zip') as source,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as destination:
 asc=json.loads(source.read('Data/poe1/zh-rTW/ascendancy_by_id.json'))
 ui=json.loads(source.read('Data/poe1/ko-KR/ui.json'))['entries']
 ui.update(json.loads(source.read('Data/poe1/ko-KR/passives.json'))['entries'])
 assert all(name in ui or name in ['Juggernaut','Warden'] for name in asc['templates'].values())
 for entry in source.infolist():
  if entry.filename=='package-files.json':continue
  content=source.read(entry)
  content,edits=patch_dictionary(entry.filename,content);changes.extend(edits)
  if entry.filename=='PoE1-3.30/Launch.lua':content=content.replace(b'r12.1',b'r12.2')
  elif entry.filename=='launcher/Umaipoe-PoB.exe':content=launcher.read_bytes()
  elif entry.filename=='launcher/launcher.json':content=(out/'launcher.json').read_bytes()
  elif entry.filename=='먼저_읽기.txt':content=notes.encode()+b'\n'+content
  destination.writestr(entry,content);manifest[entry.filename]=hashlib.sha256(content).hexdigest()
 destination.writestr('r12.2_패치노트.txt',notes.encode());manifest['r12.2_패치노트.txt']=hashlib.sha256(notes.encode()).hexdigest()
 asc['entries']={key:({'Juggernaut':'저거넛','Warden':'워든'}.get(name) or ui[name]) for key,name in asc['templates'].items()}
 asc['source_files']=['Ascendancy.Id and Korean game names; class labels only']
 name='Data/poe1/ko-KR/ascendancy_by_id.json';content=json.dumps(asc,ensure_ascii=False,separators=(',',':')).encode()
 destination.writestr(name,content);manifest[name]=hashlib.sha256(content).hexdigest()
 name='Data/poe1/ko-KR/ui_terminology.json';content=json.dumps({'source_files':['PoB contextual UI terminology corrections'], 'entries':UI},ensure_ascii=False,separators=(',',':')).encode()
 destination.writestr(name,content);manifest[name]=hashlib.sha256(content).hexdigest()
 destination.writestr('package-files.json',json.dumps(manifest,indent=2).encode())
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

payload={'schema':1,'sequence':100007,'minLauncher':1,'version':'r12.2','healthRequired':True,'koreanToolsRequired':True,'url':'https://github.com/canfisher/umaipoe-pob/releases/download/r12.2/Umaipoe-PoB-r12.2.zip','sha256':digest(target),'bytes':target.stat().st_size}
(out/'release-payload.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
(out/'SHA256SUMS.txt').write_text('\n'.join(digest(out/n)+'  '+n for n in ['Umaipoe-PoB.exe',target.name])+'\n',encoding='utf-8')
subprocess.run([str(root/'work/pob-release-cli/Manifest.exe'),'sign',str(out/'latest.json'),str(out/'release-payload.json')],check=True)
(out/'terminology-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print('Terminology changes:',len(changes))
print(json.dumps(payload))
