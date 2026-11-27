# umaipoe-pob
우마이 한글 PoB 공개 배포 · 서명된 자동 업데이트와 버전별 패치노트. 개인 빌드·설정은 업로드하지 않습니다.

## 클라우드에서 수정하기

Codex Cloud에서 `canfisher/umaipoe-pob`의 `main`을 연결하고 Python 3.11 이상으로 작업합니다. `tools/settings_ko.py`에 r13.9 설정 탭 한글화 소스가 있습니다. 배포 ZIP의 기준 버전과 SHA-256은 `tools/prepare.py`에 기록되어 있습니다.

```sh
python tools/prepare.py
python tools/prepare.py --output artifacts/Umaipoe-PoB-r13.9-candidate.zip
```

첫 명령은 공개 r13.9의 SHA-256을 확인하고 수정 대상과 번역을 검증합니다. 두 번째 명령은 같은 검증을 통과한 Windows 테스트 ZIP을 만듭니다. 두 명령 모두 다운로드한 원본을 `artifacts/`에 보관합니다. 원본 ZIP을 이미 갖고 있으면 `--base-zip`으로 경로를 지정할 수 있습니다.

Windows에서는 `--native`를 추가하면 원본과 수정본의 PoB 엔진으로 대표 설정 문구를 직접 비교합니다. 공개 자동 업데이트에는 새 릴리스 버전과 검증을 마친 ZIP, 기존 배포 키로 서명한 `latest.json`이 필요합니다. 테스트 ZIP은 별도의 공유용 파일입니다.
