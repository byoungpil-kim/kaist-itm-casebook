# KAIST ITM 사례연구 라이브러리 (ITM Case Study Library)

KAIST 기술경영전문대학원(I&TM) 석사과정 졸업 사례연구 가운데 우수사례를 선별하여
웹 기사 형태로 소개하는 정적 웹사이트입니다.
[아산기업가정신리뷰(AER)](https://asan-aer.org/case/)를 벤치마크하고,
[ITM 홈페이지](https://itm.kaist.ac.kr)의 디자인 아이덴티티(Pretendard, KAIST 블루 #0055C7)를 따릅니다.

## 구성

- **사례 36편** (2020 봄 ~ 2026 봄 발표분, 김의석 교수 1차 선정본)
- 사례별 **매거진형 기사** (원문 목차 구조를 유지한 요약 + 핵심 그림·표 + 연구 요약 + 시사점)
- 사례별 **원문 전체 열람 페이지** (보고서 본문을 웹 열람용으로 변환)
- 메인 페이지 **2축 필터**: 기술경영 쟁점(9개) × 산업 분류(8개) + 키워드 검색

## 폴더 구조

```
├── index.html              # 메인 (카드 목록 + 필터 + 검색)
├── cases/                  # 사례 기사 36편  ({사례ID}.html)
├── fulltext/               # 원문 전체 열람 페이지  ({사례ID}/index.html + img/)
├── assets/
│   ├── style.css           # 디자인 시스템 전체
│   ├── meta.json           # 사례 메타데이터 (제목·저자·지도교수·분류 등) — 빌드 입력
│   └── img/{사례ID}/       # 기사에 삽입된 원문 그림
└── _build/                 # 빌드 도구 및 콘텐츠 원본 (배포에는 불필요)
    ├── build.py            # index.html + cases/*.html 생성기
    ├── gen_fulltext2.py    # fulltext 생성기 (재생성 시 외부 자료 필요 — CLAUDE.md 참조)
    ├── cases_src/          # 기사 본문 조각 ({사례ID}_body.html) — 기사 수정은 여기서
    ├── extract/            # 원문 보고서 텍스트 추출본 (사실 검증용)
    └── WRITING_GUIDE.md    # 기사 작성 스타일 가이드
```

사례 ID 규칙: `YYSSNN` — 앞 두 자리 졸업발표연도, 가운데 두 자리 `01`=봄 / `02`=가을, 뒤 두 자리 가나다순 일련번호.
(예: `240105` = 2024년 봄 5번)

## 로컬 미리보기

정적 사이트이므로 아무 웹서버로나 열 수 있습니다.

```bash
python -m http.server 8000
# → http://localhost:8000
```

`index.html`을 파일로 직접 열어도 동작합니다(검색·필터 포함).

## 콘텐츠 수정 후 재빌드

기사 본문은 `_build/cases_src/{사례ID}_body.html`, 메타데이터는 `assets/meta.json`을 수정한 뒤:

```bash
python3 _build/build.py
```

`index.html`과 `cases/*.html`이 재생성됩니다. 자세한 규칙과 작업 절차는 **CLAUDE.md**를 참조하세요.

## GitHub Pages 배포

저장소 Settings → Pages → Branch를 `main`(root)으로 지정하면 그대로 배포됩니다.
루트의 `.nojekyll` 파일이 `_build/` 폴더(언더스코어 시작)의 무시를 방지합니다.
`_build/`를 배포에서 제외하고 싶다면 배포 브랜치에서 해당 폴더만 제거하면 됩니다.

## 저작권 및 이용 안내

- 각 사례연구의 저작권은 원저자(KAIST ITM 석사과정 졸업생)와 KAIST 기술경영전문대학원에 있습니다.
- 게시된 기사는 원문 보고서를 요약·재구성한 것으로, **원저자의 최종 컨펌 전 초안** 상태일 수 있습니다.
- 무단 전재 및 재배포를 금합니다.
