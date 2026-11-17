#pragma once
#include "launcher_strings.h"

#define UMAIPOE_RELEASE "r11.2"
static const wchar_t* kUmaipoeDownload = L"https://umaipoe.tistory.com/66";
static const wchar_t* kUmaipoeRepository = L"https://github.com/canfisher/umaipoe-pob";

inline void UmaipoeStrings(LauncherStrings& s)
{
    s.appSubtitle = u8"우마이 한국어 빌드·파밍 도구 · r11.2";
    s.aboutTagline = u8"한국어 PoB 유지보수와 플레이 편의 도구";
    s.aboutBody = u8"우마이 한글 PoB\n한글화·오류 수정·파밍 도구를 우마이 배포판에서 관리합니다.\n비공식 팬 도구이며 Grinding Gear Games와 제휴 관계가 없습니다.\n오픈소스 라이선스와 구성 요소 고지는 동봉한 LICENSE·NOTICE 파일에 보존되어 있습니다.\n궁금한 점이나 피드백은 블로그 댓글로 남겨 주세요.";
    s.clSearchHint = u8"버전·수정 내용 검색…";
    s.clCurrent = u8"현재 버전";
    s.changelog = u8"우마이 패치노트";
    s.linkGroupTools = u8"우마이 도구";
    s.atlasPlanner = u8"아틀라스 파밍 도구";
    s.timelessJewel = u8"무궁한 주얼";
    s.regexTool = u8"게임 검색식";
    s.warehouseTool = u8"보관함 수익 기록";
    s.editorName = u8"번역 편집기";
    s.tipFilter = u8"아이템 필터를 편집하고 드롭 표시를 미리 봅니다";
    s.tipAtlas = u8"원하는 파밍을 골라 노드를 연결하고 저장합니다";
    s.tipTimeless = u8"주얼 번호별 노드 변화와 원하는 효과를 찾습니다";
    s.tipRegex = u8"원하는 속성을 골라 게임 검색식을 만듭니다";
    s.tipWarehouse = u8"보관함 기록을 비교해 파밍 수익을 확인합니다";
}
