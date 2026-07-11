# CLAUDE.md — 에이전트 작업지시서

이 저장소는 **KAIST ITM 사례연구 라이브러리** 정적 웹사이트다.
이 문서는 Claude Code(및 기타 AI 에이전트)가 이 저장소를 유지보수할 때 반드시 따라야 할
규칙과 작업 절차를 정의한다.

## 1. 프로젝트 한눈에 보기

- 순수 정적 사이트. 프레임워크·빌드체인 없음. HTML + 단일 CSS + 바닐라 JS(필터/검색)만 사용한다.
- `index.html`과 `cases/*.html`은 **생성물**이다. 직접 수정하지 말고 원본을 고친 뒤 재빌드한다.
  - 기사 본문 원본: `_build/cases_src/{사례ID}_body.html`
  - 메타데이터: `assets/meta.json`
  - 생성기: `python3 _build/build.py`
- `fulltext/`(원문 전체 열람)와 `assets/img/`(기사 그림)는 이미 생성 완료된 산출물이며,
  일반 유지보수에서 재생성할 일이 거의 없다(재생성 제약은 §6 참조).
- 디자인은 itm.kaist.ac.kr 를 따른다. 임의로 다른 디자인 언어를 도입하지 않는다.

## 2. 사용자 요청 규칙

이 규칙들은 사용자가 요청한 사항이다.

1. **우수사례 선정 여부를 표시하지 않는다.** 카드·기사 어디에도 우수/선정 배지를 넣지 않는다.
   (`assets/meta.json`의 `excellent`, `qual` 필드는 내부 참고용으로만 존재한다. 화면에 노출 금지.)
2. **메인 히어로에 통계(선정 사례 수·우수사례 수·발표연도)를 표시하지 않는다.**
3. **원문 전체 보기는 '흐르는 본문형 HTML'이다.** PDF 페이지를 그대로 보여주는 방식(페이지 단위
   렌더링, PDF 임베드) 금지. 목차는 생략 가능. 같은 창에서 열리며(새창 금지) 왼쪽 사이드바가
   유지된다. 돌아가기 문구는 "요약으로 돌아가기" / "← 요약 보기"를 사용한다.
4. **PDF 다운로드는 검수 목적으로 임시 허용 상태다.** `pdf/{사례ID}.pdf`(학기 모음집은 해당
   사례만 분할한 파일)와 요약·원문 페이지의 "PDF 내려받기" 버튼을 유지한다. 변환 검수가 끝나고
   정식 공개가 결정되면 사용자 지시에 따라 버튼과 pdf/ 폴더를 제거한다.
5. **기사의 '연구 요약'(keybox)은 원문 초록(ABSTRACT) 내용 기반 불릿**이다. 핵심 결론과 시사점을
   포함하되, "연구 질문:", "방법론:" 같은 라벨 접두어를 붙이지 않는다.
6. **모든 페이지에서 왼쪽 사이드바(기술경영 쟁점 / 산업 분류)를 유지한다.** 사례 페이지의
   사이드바 항목은 `index.html?issue=…` / `?cat=…` 링크로 동작한다.
7. **그림·표 출처 표기**: 원문 보고서에 출처가 명시된 그림만 그 실제 출처를 표기한다.
   원문에 출처가 없으면 출처를 표기하지 않는다. "(출처: 원문 보고서)" 같은 표기 금지.
8. **사실 충실성**: 기사·원문 페이지의 수치·연도·고유명사·인용은 원문 보고서
   (`_build/extract/{사례ID}.txt`)와 일치해야 한다. 원문에 없는 내용을 창작하지 않는다.
9. **기사 구조는 원문 목차를 따른다.** 장·절 제목은 원문 표현을 유지한다(경미한 축약 허용).
   AI 느낌의 재창작 소제목 금지. 상세 스타일은 `_build/WRITING_GUIDE.md` 참조.
10. **원문 전체 보기 버튼은 새 창으로 연다.** (`target="_blank" rel="noopener"` — build.py에 반영됨)
11. **기술경영 쟁점은 사례당 2~5개 복수 지정한다.** `assets/meta.json`의 `issues` 배열이 원본이며
    첫 항목이 대표 쟁점이다(`issue` 필드에 자동 복사). 카드 칩·사이드바 필터·사례 페이지 하이라이트는
    모든 쟁점에 반응한다. 재분류 시 원본 엑셀(Case list_ITM_선정.xlsx)의 키워드 컬럼을 참고한다.
12. **카드와 사례 페이지에 `[No. 사례ID]`를 표시한다.** 선정 엑셀 목록과 매칭하기 위한 것이므로 제거하지 않는다.
13. **검색엔진 인덱싱 금지 상태를 유지한다.** 대외 공개 전까지 루트 `robots.txt`(Disallow: /)와
    모든 페이지의 `<meta name="robots" content="noindex, nofollow">`를 제거하지 않는다.
    (대외 공개가 결정되면 사용자 지시에 따라 해제)
14. **하단 배너의 저작권 고지를 유지한다.** 저작권은 원저자 귀속, 무단 전재·복제·배포 금지,
    활용 시 사전 허락 필요 문구. 파란 서브내비 밴드는 사용하지 않는다.
15. **작업 중(WIP) 표시를 유지한다.** 정식 배포 전까지 ① 메인·요약·원문 페이지 상단 배너의
    WIP 고지 문구(수정 요청: byoungpil.kim@kaist.ac.kr)와 ② 전 페이지 워터마크(style.css의
    `body::after`)를 제거하지 않는다.
16. **카드에 이미지(SVG 아트·로고 등)를 넣지 않는다.** 실험 후 제거하기로 확정된 사항이다
    (텍스트 중심 카드 유지). `assets/img/cards/`와 `_build/gen_cardart.py`가 남아 있다면 삭제해도 된다.

## 3. 파일 구조와 데이터 흐름

```
assets/meta.json  ─┐
                   ├─→ python3 _build/build.py ─→ index.html, cases/{id}.html
_build/cases_src/{id}_body.html ─┘

_build/extract/{id}.txt (+ imgpool, 저장소 외부) ─→ _build/gen_fulltext2.py ─→ fulltext/{id}/
```

`assets/meta.json` 필드:

| 필드 | 의미 | 비고 |
|---|---|---|
| `id` | 사례 ID (YYSSNN) | 파일명 전체와 연동 |
| `title`, `author`, `advisor` | 제목·연구자·지도교수 | advisor 없으면 빈 문자열("-"로 표시됨) |
| `issues` | 기술경영 쟁점 목록 (9종 중 2~5개) | build.py 상단 `ISSUES` 목록과 일치해야 함. 첫 항목 = 대표 쟁점 |
| `issue` | 대표 쟁점 (`issues[0]`) | 브레드크럼 표시용. `issues` 변경 시 함께 갱신 |
| `category` | 산업 분류 (8종) | build.py 상단 `CATS` 목록과 일치해야 함 |
| `firm`, `firmInfo`, `field` | 대상 기업 정보 | |
| `year`, `semester`, `pub` | 발표 시기 | |
| `excellent`, `qual`, `themes` | 내부 참고용 | **화면 노출 금지** |

기사 조각(`{id}_body.html`)의 구성 요소(순서 고정):
`<p class="lead">` → `<div class="keybox">`(연구 요약) → 원문 목차 따른 `<h2>/<h3>` 본문
→ `<div class="pull">`(원문 문장 기반 풀쿼트 1~2개) → `<figure>` 3~4개 → `<div class="insight">`(결론 및 시사점).

## 4. 자주 하는 작업 절차

### 기사 내용 수정 (오탈자, 문장, 그림 교체 등)
1. `_build/cases_src/{id}_body.html` 수정. 사실관계는 `_build/extract/{id}.txt`로 검증.
2. 그림 교체 시 새 이미지를 `assets/img/{id}/`에 넣고 `../assets/img/{id}/파일명` 경로로 참조.
3. `python3 _build/build.py` 실행.
4. 검증(§5) 후 커밋.

### 사례 삭제 (예: 최종 15~20편 선정 반영)
1. `assets/meta.json`에서 해당 항목 제거.
2. `python3 _build/build.py` (index와 prev/next 링크가 함께 갱신된다).
3. `cases/{id}.html`, `fulltext/{id}/`, `assets/img/{id}/`, `_build/cases_src/{id}_body.html` 제거.

### 사례 추가
1. 원문 보고서에서 텍스트 추출(`pdftotext -layout`) → `_build/extract/{id}.txt`.
2. `_build/WRITING_GUIDE.md`와 기존 기사 2~3편을 정독한 후 §2 규칙에 맞춰
   `_build/cases_src/{id}_body.html` 작성. 그림은 원문에서 추출해 `assets/img/{id}/`에 저장.
3. `assets/meta.json`에 항목 추가 (issue/category는 기존 9/8종 중에서 선택).
4. 원문 전체 페이지 생성(§6 제약 확인) 또는 기존 사례의 `fulltext/{id}/index.html`을 복제해
   같은 마크업 구조(`.ft-body`, `.ftcap`, `.ftsrc`, `.ftfig`)로 수작업 작성.
5. `python3 _build/build.py` → 검증 → 커밋.

### 분류 체계 변경
`_build/build.py` 상단의 `ISSUES` / `CATS` 배열과 `assets/meta.json`의 각 항목을 함께 수정한 뒤 재빌드.
사례 페이지 사이드바는 빌드 시 자동 반영된다.

### 디자인 수정
`assets/style.css` 하나만 수정한다(모든 페이지가 공유). 색·간격 토큰은 파일 상단 `:root` 변수.
fulltext 페이지에만 적용되는 스타일은 각 `fulltext/{id}/index.html` 내 `<style>` 블록에 있음을 유의
(수정 시 36개 파일 일괄 치환 필요 — sed/스크립트 사용).

## 5. 변경 후 검증 체크리스트

```bash
python3 _build/build.py                 # 에러 없이 36 cards / 36 case pages
python -m http.server 8000              # 육안 확인
```

추가로 스크립트 검증(권장):
- 모든 `cases/*.html`의 `<img src>` 경로가 실제 파일로 해석되는지
- `cases/*.html`에 `chip gold`(우수 배지), `pdf` 링크가 없는지
- 각 사례 페이지에 `원문 전체 보기` 버튼과 사이드바(`facets`)가 있는지
- `fulltext/{id}/index.html`의 `img/…` 참조가 깨지지 않았는지

## 6. 원문 전문(fulltext) 재생성 제약 — 중요

`_build/gen_fulltext2.py`는 다음 외부 자료를 요구하며, **이 저장소에는 포함되어 있지 않다**:
- `_build/imgpool/{id}/f-*.png` — 원문 PDF에서 `pdfimages -png -p`로 추출한 그림 풀(총 수백 MB)
- 원문 PDF 원본 (별도 보관: 발주자 로컬 `C:\claude\itm-cases\ITM 사례 전체\`)

따라서 **기존 `fulltext/`를 삭제하거나 통째로 재생성하지 말 것.** 부분 수정은 해당
`fulltext/{id}/index.html`을 직접 편집한다. 전면 재생성이 필요하면 사용자에게 원문 PDF
제공을 요청한 뒤: ① `pdftotext -layout`으로 `_build/extract/` 갱신 ② `pdfimages`로 imgpool 구축
(폭<220px·높이<120px·8KB 미만 파일 제거) ③ `python3 _build/gen_fulltext2.py {id}` 실행.

특수 사례 **210107(서용진, 대우조선해양)**: 원문이 스캔본(텍스트 레이어 없음)이라
페이지 이미지를 판독·전사한 `_build/210107_full.html`이 본문 원본이다. 이 사례의 fulltext는
`gen_fulltext2.py`의 `gen_scanned()` 경로로 생성된다.

## 7. 알려진 한계 (이슈 대응 시 참고)

- fulltext 본문에 간헐적 띄어쓰기 오류가 있다(원문 PDF의 강제 줄바꿈 지점 병합 시 한글-한글
  경계는 붙여쓰기 규칙 적용). 개별 신고 건은 해당 `fulltext/{id}/index.html`에서 직접 수정.
- fulltext의 그림 배치는 "캡션 직후 + 같은/인접 페이지" 휴리스틱이라 드물게 캡션-그림이
  어긋날 수 있다. 발견 시 해당 `<figure class="ftfig">` 블록을 올바른 캡션 아래로 이동.
- 230214(장영준, 토스증권)는 원문에 지도교수 표기가 없어 advisor가 빈 값이다.
- 기사들은 원저자(학생) 최종 컨펌 전 초안이다. 저자 요청 수정이 들어올 수 있다.

## 8. 프로젝트 로드맵 (참고)

1. ~~1차 선정 36편 사이트 구축~~ (완료)
2. 36편 추가 평가 → 최종 15~20편 선정 (선정 기준: 분석 깊이, 이론 정합성, 최신성, 분야 다양성 등.
   내부 참고용 `qual` 점수 활용 가능) → §4 "사례 삭제" 절차로 반영
3. 원저자 컨펌 및 수정 반영
4. GitHub Pages(또는 학교 서버) 공개
