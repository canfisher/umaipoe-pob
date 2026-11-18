from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parents[2]
previous = root / "outputs/pob330-r13.1"
out = root / "outputs/pob330-r13.2"
version = "r13.2"
feed = f"https://github.com/canfisher/umaipoe-pob/releases/download/{version}/"
out.mkdir(exist_ok=True)
notes = """우마이 한글 PoB r13.2 · 개인 빌드 목록

처음 실행하면 빈 목록에서 시작합니다. 저장한 빌드는 Windows 사용자별로 보관하며 다음 실행과 업데이트 뒤에도 같은 목록을 사용합니다. 이전 설치 폴더를 불러오려면 Shift를 누른 채 실행하고 ‘기존 폴더 가져오기’를 선택하세요. 이전 폴더에서 설정을 가져올 때는 가져온 빌드가 있는 내 폴더를 사용합니다. 기존에 직접 지정한 저장 경로는 그대로 사용할 수 있습니다.
창 아이콘이 간헐적으로 조회되지 않아 시작 중 종료되는 문제를 수정했습니다. 창과 작업표시줄에는 같은 우마이 아이콘을 사용합니다.
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
assert launcher.is_file()
base = dict(schema=1, sequence=100010, minLauncher=1, version=version)
sign("launcher", dict(base, launcherVersion=5, kind="launcher", url=feed+launcher.name,
                     sha256=digest(launcher), bytes=launcher.stat().st_size))
for file in ("release-notes.md", "패치노트.txt"):
    (out/file).write_text(notes, encoding="utf-8")

with zipfile.ZipFile(previous/"Umaipoe-PoB-r13.1.zip") as src, zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as dst:
    hashes = {}
    for info in src.infolist():
        name = info.filename
        if name == "package-files.json":
            continue
        data = src.read(info)
        if name == "PoE1-3.30/Modules/Main.lua":
            text = data.decode("utf-8").replace("\r\n","\n")
            start = text.index('elseif GetScriptPath() ~= "" then', text.index('local sharedUserData ='))
            end = text.index('else\n', start)
            text = text[:start] + """elseif os.getenv("LOCALAPPDATA") and os.getenv("LOCALAPPDATA") ~= "" then
        local accountRoot = os.getenv("LOCALAPPDATA"):gsub("\\\\", "/") .. "/UmaipoePoB"
        MakeDir(accountRoot)
        MakeDir(accountRoot .. "/Auto")
        self.userPath = accountRoot .. "/Auto/UserData/"
    """ + text[end:]
            data = text.encode("utf-8")
        elif name == "PoE1-3.30/Launch.lua":
            assert b"r13.1 (3.30)" in data
            data = data.replace(b"r13.1", version.encode())
        elif name == "pob-zh.exe":
            data = (Path(__file__).resolve().parent/"host-build/pob-zh.exe").read_bytes()
        elif name == "launcher/Umaipoe-PoB.exe":
            data = launcher.read_bytes()
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
