from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile

root=Path(__file__).resolve().parents[2]
old=root/'outputs/pob330-r12';out=root/'outputs/pob330-r12.1';out.mkdir(exist_ok=True)
notes='''우마이 한글 PoB r12.1 — 패시브 탭 번역 수정

- 빌드 화면의 Tree 탭에 잘못 표시되던 '나무'를 '패시브'로 수정했습니다.
- 기존 빌드·설정과 계산 결과는 변경하지 않습니다.
- Umaipoe-PoB.exe를 다시 실행하면 업데이트를 확인합니다. 이미 열린 창은 저장 후 종료하고 다시 열어 주세요.
- r12의 기능과 미검증 항목은 그대로이며 이번 변경은 표시 용어 수정입니다.
'''
for name in ['release-notes.md','패치노트.txt']:(out/name).write_text(notes,encoding='utf-8')
target=out/'Umaipoe-PoB-r12.1.zip';assert not target.exists()
changes={};manifest={}
with zipfile.ZipFile(old/'Umaipoe-PoB-r12.zip') as source,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as destination:
 for entry in source.infolist():
  if entry.filename=='package-files.json':continue
  content=source.read(entry)
  if entry.filename=='Data/poe1/ko-KR/ui.json':
   data=json.loads(content);assert data['entries']['Tree']=='나무';data['entries']['Tree']='패시브'
   content=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode();changes[entry.filename]=content
  elif entry.filename=='PoE1-3.30/Launch.lua':
   content=content.replace(b'r12',b'r12.1');changes[entry.filename]=content
  elif entry.filename=='먼저_읽기.txt':content=notes.encode()+b'\n'+content
  destination.writestr(entry,content);manifest[entry.filename]=hashlib.sha256(content).hexdigest()
 destination.writestr('r12.1_패치노트.txt',notes.encode());manifest['r12.1_패치노트.txt']=hashlib.sha256(notes.encode()).hexdigest()
 destination.writestr('package-files.json',json.dumps(manifest,indent=2).encode())
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
shutil.copy2(old/'Umaipoe-PoB.exe',out/'Umaipoe-PoB.exe')
payload={'schema':1,'sequence':100005,'minLauncher':1,'version':'r12.1','healthRequired':True,'koreanToolsRequired':True,'url':'https://github.com/canfisher/umaipoe-pob/releases/download/r12.1/Umaipoe-PoB-r12.1.zip','sha256':digest(target),'bytes':target.stat().st_size}
(out/'release-payload.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
(out/'SHA256SUMS.txt').write_text('\n'.join(digest(out/n)+'  '+n for n in ['Umaipoe-PoB.exe',target.name])+'\n',encoding='utf-8')
subprocess.run([str(root/'work/pob-release-cli/Manifest.exe'),'sign',str(out/'latest.json'),str(out/'release-payload.json')],check=True)
(out/'change-summary.json').write_text(json.dumps({'dictionaryKey':'Tree','before':'나무','after':'패시브','baseRelease':'r12','version':'r12.1'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(payload))
