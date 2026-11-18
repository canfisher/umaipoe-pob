from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parents[2]
previous = root / "outputs/pob330-r13"
out = root / "outputs/pob330-r13.1"
version = "r13.1"
feed = f"https://github.com/canfisher/umaipoe-pob/releases/download/{version}/"
out.mkdir(exist_ok=True)
notes = """우마이 한글 PoB r13.1

스킬 탭에서 선택한 젬 이름을 한국어로 표시합니다. 젬 선택 목록과 같은 번역 사전으로 이름과 표시 폭을 처리합니다. 영어 모드에서는 영어 이름을 표시합니다.
빌드를 다시 열어도 같은 방식으로 표시하며, 검색·편집 중에는 입력한 문자를 그대로 보여 줍니다.
Umaipoe-PoB.exe를 다시 실행하면 자동 업데이트를 확인합니다.
"""

def save(name, obj):
    (out / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def sign(name, payload):
    save(name+"-payload.json", payload)
    envelope = "latest" if name == "release" else name
    subprocess.run([root/"work/pob-release-cli/Manifest.exe", "sign",
                    out/(envelope+".json"), out/(name+"-payload.json")], check=True)

def replace_once(data, old, new):
    assert data.count(old) == 1, old
    return data.replace(old, new)

archive = out / f"Umaipoe-PoB-{version}.zip"
if archive.exists():
    raise SystemExit("Archive already exists")
launcher = out / "Umaipoe-PoB.exe"
shutil.copy2(previous / launcher.name, launcher)
base = dict(schema=1, sequence=100009, minLauncher=1, version=version)
sign("launcher", dict(base, launcherVersion=4, kind="launcher", url=feed+launcher.name,
                     sha256=digest(launcher), bytes=launcher.stat().st_size))
for file in ("release-notes.md", "패치노트.txt"):
    (out/file).write_text(notes, encoding="utf-8")

with zipfile.ZipFile(previous/"Umaipoe-PoB-r13.zip") as src, zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as dst:
    hashes = {}
    for info in src.infolist():
        name = info.filename
        if name == "package-files.json":
            continue
        data = src.read(info)
        if name == "PoE1-3.30/Classes/GemSelectControl.lua":
            marker = b'self:EditControl(anchor, rect, nil, nil, "^ %a\':-")'
            data = replace_once(data, marker, marker+b"\n\tself.translateInactiveName = true")
        elif name == "PoE1-3.30/Classes/EditControl.lua":
            marker = b'self.controls.scrollBarH:SetContentDimension(InputStringWidth(textHeight, self.font, self.buf) + 2, width - 4'
            data = replace_once(data, marker, b'local measure = self.translateInactiveName and not self.hasFocus and DrawStringWidth or InputStringWidth\n\t\t'+marker.replace(b'InputStringWidth(', b'measure('))
            marker = b'DrawInputString(-self.controls.scrollBarH.offset, -self.controls.scrollBarV.offset, "LEFT", textHeight, self.font, self.buf)'
            data = replace_once(data, marker, b'local drawName = self.translateInactiveName and DrawString or DrawInputString\n\t\t\t\t'+marker.replace(b'DrawInputString(',b'drawName('))
        elif name == "PoE1-3.30/Launch.lua":
            assert b"r13 (3.30)" in data
            data = data.replace(b"r13", version.encode())
        elif name == "launcher/launcher.json":
            data = (out/"launcher.json").read_bytes()
        elif name == "먼저_읽기.txt":
            data = notes.encode()+b"\n"+data
        hashes[name] = hashlib.sha256(data).hexdigest()
        dst.writestr(info, data)
    dst.writestr("package-files.json", json.dumps(hashes).encode())
sign("release",dict(base,healthRequired=True,koreanToolsRequired=True,url=feed+archive.name,
                   sha256=digest(archive),bytes=archive.stat().st_size))
(out/"SHA256SUMS.txt").write_text("".join(f"{digest(p)}  {p.name}\n" for p in (launcher,archive)),encoding="utf-8")
