from pathlib import Path
import hashlib,json,subprocess,zipfile,shutil

root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
old=root/'outputs/pob330-r12.2'
out=root/'outputs/pob330-r13'
app=out/'Umaipoe-PoB-r13'
notes='''우마이 한글 PoB r13 — 제웅·살덩이 조합 비교

- 아이템 탭의 제웅 네 부위 아래에 ‘살덩이 조합 비교’를 추가했습니다.
- 현재 빌드를 복사한 계산에서 머리·몸통·팔·다리를 선택하고 실제 수치를 편집합니다. 현재 빌드의 장비·설정은 바뀌지 않습니다.
- 일반 몬스터·지도 보스·일반 엔드보스·우버 보스와 플라스크 활성 상태를 양쪽에 동일하게 적용합니다.
- 깃발·언데드·야수·동물 피격·희귀 몬스터·시체 공급·생명력 회생·저주 조건을 직접 선택합니다.
- 피해·자원, 생존·회복, 살덩이 참고값으로 나누어 현재/비교 조합/차이를 보여 줍니다.
- 미계산 효과의 개수와 내용을 구분합니다. 차이가 0이라고 효과가 없다고 단정하지 않습니다.
- ‘결과 복사’는 조건과 실제 수치가 포함된 보고서, ‘조합 코드 복사’는 비교한 장비·조건을 포함한 PoB 가져오기 코드입니다.
- 복사한 코드는 가져오기/내보내기에서 ‘새 빌드로 가져오기’를 선택한 뒤 다른 이름으로 저장하세요. 비교 창을 닫으면 임시 선택은 사라집니다.
- 기본 창에서 제목·버튼이 잘리지 않도록 조정했습니다. 무한대 피격 한계와 미계산 값을 구분합니다.

사용 순서
1. 기존 PoB 코드 또는 XML을 가져오고 사용할 스킬·장비 세트와 주력 스킬을 선택합니다.
2. 아이템 → 살덩이 조합 비교에서 부위를 고릅니다. 새 항목은 중간 수치이므로 ‘수치·효과’에서 보유품 또는 구매 예정품의 실제 값으로 바꿉니다.
3. 대상과 조건을 고른 뒤 ‘비교 계산’을 누릅니다. 설정 변경 후에는 다시 계산해야 복사할 수 있습니다.
4. 피해만 보지 말고 생존·회복 페이지도 확인합니다. 조합을 보관하려면 ‘조합 코드 복사’를 사용합니다.

계산 범위
- 다른 장비, 패시브, 젬, 충전·처치 설정과 수동 적 능력치 등은 가져온 빌드 기준입니다. 대상 종류를 변경하면 이전 보스의 특정 스킬 프리셋을 해제합니다.
- 자동 최적 조합 탐색이나 시세 순위 기능은 아닙니다. 실제 처치 시간·강화 지도 보스의 미공개 수치·주기 회복의 상시 유지·충전 확률의 상시 최대 중첩은 보장하지 않습니다.
- 전체 DPS는 원본에서 포함하도록 지정한 스킬만 계산합니다. 미포함 스킬만 있는 경우 ‘—/미계산’으로 표시합니다.
- 계산 엔진의 기존 미지원 효과와 수동 설정은 유지됩니다. 신규 비교 기능이 모든 게임 효과를 지원한다는 뜻은 아닙니다.
- r12.2와 사용자 빌드·설정을 보존합니다. Umaipoe-PoB.exe 재실행 시 업데이트 확인 후 적용하며, 검증 실패 시 기존 버전으로 복구합니다.
'''
for name in ['release-notes.md','패치노트.txt']:(out/name).write_text(notes,encoding='utf-8')
shutil.copy2(old/'Umaipoe-PoB.exe',out/'Umaipoe-PoB.exe')
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
launcher={'schema':1,'sequence':100008,'minLauncher':1,'launcherVersion':4,'kind':'launcher','version':'r13','url':'https://github.com/canfisher/umaipoe-pob/releases/download/r13/Umaipoe-PoB.exe','sha256':digest(out/'Umaipoe-PoB.exe'),'bytes':(out/'Umaipoe-PoB.exe').stat().st_size}
(out/'launcher-payload.json').write_text(json.dumps(launcher,separators=(',',':')),encoding='utf-8')
signer=root/'work/pob-release-cli/Manifest.exe'
subprocess.run([str(signer),'sign',str(out/'launcher.json'),str(out/'launcher-payload.json')],check=True)
changes={name:(app/name).read_bytes() for name in ['PoE1-3.30/Launch.lua','PoE1-3.30/Classes/ItemsTab.lua','PoE1-3.30/Modules/WickermanCompare.lua']}
changes['launcher/launcher.json']=(out/'launcher.json').read_bytes()
changes['r13_살덩이_비교_사용법.txt']=notes.encode()
for name in ['WickermanCompare.lua','patch.py','package.py','fixture.xml','tests.lua','crosscheck.lua','conditions.lua','run-native.py']:
    changes['r13-source/'+name]=(work/name).read_bytes()
archive=out/'Umaipoe-PoB-r13.zip'
assert not archive.exists(),'Preserve completed package; version before replacing.'
manifest={}
with zipfile.ZipFile(old/'Umaipoe-PoB-r12.2.zip') as src,zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
    for entry in src.infolist():
        if entry.filename=='package-files.json':continue
        data=changes.pop(entry.filename,src.read(entry))
        if entry.filename=='먼저_읽기.txt':data=notes.encode()+b'\n'+data
        dst.writestr(entry,data);manifest[entry.filename]=hashlib.sha256(data).hexdigest()
    for name,data in changes.items():
        dst.writestr(name,data);manifest[name]=hashlib.sha256(data).hexdigest()
    dst.writestr('package-files.json',json.dumps(manifest,indent=2).encode())
payload={'schema':1,'sequence':100008,'minLauncher':1,'version':'r13','healthRequired':True,'koreanToolsRequired':True,'url':'https://github.com/canfisher/umaipoe-pob/releases/download/r13/Umaipoe-PoB-r13.zip','sha256':digest(archive),'bytes':archive.stat().st_size}
(out/'release-payload.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
subprocess.run([str(signer),'sign',str(out/'latest.json'),str(out/'release-payload.json')],check=True)
(out/'SHA256SUMS.txt').write_text('\n'.join(digest(out/name)+'  '+name for name in ['Umaipoe-PoB.exe',archive.name])+'\n',encoding='utf-8')
print(json.dumps(payload))
