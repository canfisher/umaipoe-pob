import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import zipfile

from settings_ko import LABELS, prepare


VERSION = 'r13.9'
ZIP_NAME = f'Umaipoe-PoB-{VERSION}.zip'
BASE_URL = f'https://github.com/canfisher/umaipoe-pob/releases/download/{VERSION}/{ZIP_NAME}'
BASE_SHA256 = '7174040fa67e30c6d00dedccfb7d9b64fe4943aa3e2f32c4ffd1ce18d14d498c'
TARGETS = (
    'Data/poe1/ko-KR/ui.json',
    'PoE1-3.30/Classes/ConfigTab.lua',
    'PoE1-3.30/Modules/ConfigOptions.lua',
    'PoE1-3.30/Modules/BuildDisplayStats.lua',
    'PoE1-3.30/Launch.lua',
)
PROBES = {
    'Show All Configurations': '모든 설정 표시',
    '^7Mana Burn Stacks:': '마나 연소 중첩',
    '^7Enemy ^x3F6DB3Cold Resistance:': '저항:',
    'Do your minions have Onslaught?': '맹공',
}


def check_sha256(path):
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != BASE_SHA256:
            raise ValueError(f'r13.9 원본의 SHA-256이 일치하지 않습니다: {path}')


def base_archive(path):
    if path.exists():
        check_sha256(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as temporary:
        download = Path(temporary) / ZIP_NAME
        with urlopen(BASE_URL, timeout=60) as response, download.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        check_sha256(download)
        download.replace(path)


def localized_files(archive, temporary):
    for name in TARGETS:
        archive.extract(name, temporary)
    patched = {name.as_posix(): content for name, content in prepare(temporary).items()}
    assert set(patched) == set(TARGETS)
    dictionary = json.loads(patched[TARGETS[0]])['entries']
    assert all(dictionary.get(key) == value for key, value in LABELS.items())
    assert '우마이 한글 PoB r13.9' in patched[TARGETS[-1]].decode()
    return patched


def native_check(archive, temporary, patched):
    engine = temporary / 'pob-zh.exe'
    for member in archive.namelist():
        if member in {'pob-zh.exe', 'pob-zh.ini'} or member.startswith('Data/poe1/'):
            parts = PurePosixPath(member).parts
            if not parts or '..' in parts or '\\' in member or ':' in member:
                raise ValueError(f'잘못된 ZIP 경로: {member}')
            archive.extract(member, temporary)
    for name in PROBES:
        before = probe(engine, name)
        if PROBES[name] in before:
            raise ValueError(f'원본에서도 번역이 발견되었습니다: {name}')
    for name, content in patched.items():
        (temporary / name).write_bytes(content)
    for name, expected in PROBES.items():
        if expected not in probe(engine, name):
            raise ValueError(f'수정본에서 번역을 찾지 못했습니다: {name}')


def probe(engine, source):
    result = subprocess.run(
        [engine, '--tr', source, 'ko-KR'], cwd=engine.parent, capture_output=True,
        encoding='utf-8', timeout=30, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f'PoB 번역 엔진 종료 코드: {result.returncode}')
    return next(line for line in result.stdout.splitlines() if 'lookup        :' in line)


def package(archive, output, patched):
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(archive.read('package-files.json'))
    for name, content in patched.items():
        manifest[name] = hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as bundle:
        for member in archive.infolist():
            if member.filename == 'package-files.json':
                bundle.writestr(member, json.dumps(manifest, ensure_ascii=False))
            elif member.filename in patched:
                bundle.writestr(member, patched[member.filename])
            else:
                bundle.writestr(member, archive.read(member))
    with zipfile.ZipFile(output) as bundle:
        for name, content in patched.items():
            if bundle.read(name) != content:
                raise ValueError(f'후보 ZIP에서 수정 파일이 일치하지 않습니다: {name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-zip', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    if args.native and sys.platform != 'win32':
        parser.error('--native requires Windows')
    path = args.base_zip or Path('artifacts') / ZIP_NAME
    if args.base_zip is None:
        base_archive(path)
    else:
        check_sha256(path)
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as temporary:
        patched = localized_files(archive, Path(temporary))
        if args.native:
            native_check(archive, Path(temporary), patched)
        if args.output:
            package(archive, args.output, patched)
    print(f'{VERSION}: {len(LABELS)}개 번역, {len(patched)}개 수정 파일 확인')


if __name__ == '__main__':
    main()
