import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'outputs/pob330-r12';app=out/'Umaipoe-PoB-r12'
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def allowed(p):
 r=p.relative_to(app);name=p.name.lower()
 return p.is_file() and not set(x.lower() for x in r.parts)&{'builds','userdata','logs','backups','pobtools','.git'} and name not in {'settings.xml','release-key.dpapi','hosts.yml','.env'} and not name.endswith(('.log','.tmp','.bak','.dpapi')) and '.saving-' not in name and 'selftest' not in name and not name.startswith(('tj_verify','filter_import_probe'))
launcher=app/'launcher';launcher.mkdir(exist_ok=True)
shutil.copy2(out/'Umaipoe-PoB.exe',launcher/'Umaipoe-PoB.exe')
payload={'schema':1,'sequence':100004,'minLauncher':1,'kind':'launcher','launcherVersion':3,'version':'r12-launcher','url':'https://github.com/canfisher/umaipoe-pob/releases/download/r12/Umaipoe-PoB.exe','sha256':digest(out/'Umaipoe-PoB.exe'),'bytes':(out/'Umaipoe-PoB.exe').stat().st_size}
(out/'launcher-payload.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
subprocess.run([str(root/'work/pob-release-cli/Manifest.exe'),'sign',str(launcher/'launcher.json'),str(out/'launcher-payload.json')],check=True)
files=sorted(p for p in app.rglob('*') if allowed(p))
(app/'package-files.json').write_text(json.dumps({p.relative_to(app).as_posix():digest(p) for p in files if p.name!='package-files.json'},indent=2),encoding='utf-8')
target=out/'Umaipoe-PoB-r12.zip';assert not target.exists(),'Preserve package before replacing'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(p for p in app.rglob('*') if allowed(p)):z.write(p,p.relative_to(app).as_posix())
release={'schema':1,'sequence':100004,'minLauncher':1,'version':'r12','healthRequired':True,'koreanToolsRequired':True,'url':'https://github.com/canfisher/umaipoe-pob/releases/download/r12/Umaipoe-PoB-r12.zip','sha256':digest(target),'bytes':target.stat().st_size}
(out/'release-payload.json').write_text(json.dumps(release,separators=(',',':')),encoding='utf-8')
(out/'SHA256SUMS.txt').write_text('\n'.join(digest(out/n)+'  '+n for n in ['Umaipoe-PoB.exe',target.name])+'\n',encoding='utf-8')
subprocess.run([str(root/'work/pob-release-cli/Manifest.exe'),'sign',str(out/'latest.json'),str(out/'release-payload.json')],check=True)
print(json.dumps(release))
