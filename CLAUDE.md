# CLAUDE.md — 에이전트 작업지시서

이 저장소는 **KAIST ITM 사례연구 라이브러리** 정적 웹사이트다.
이 문서는 Claude Code(및 기타 AI 에이전트)가 이 저장소를 유지보수할 때 반드시 따라야 할
규칙과 작업 절차를 정의한다.

## 1. 프로젝트 한눈에 보기

- 순수 정적 사이트. 프레임워크·빌드체인 없음. HTML + 단일 CSS + 바닐라 JS(필터/검색)만 사용한다.
- `index.html`은 **순수 생성물**이다(카드·필터·이전/다음 링크). 직접 수정하지 말고 `assets/meta.json`을
  고친 뒤 `python3 _build/build.py`로 재생성한다.
- `cases/*.html`은 **본문은 직접 편집, 나머지(헤더·사이드바·다운로드바 등 chrome)는 생성**이다.
  - **기사 본문**: `cases/{사례ID}.html` 안의 `<!-- BODY:START -->` ~ `<!-- BODY:END -->` 사이를
    **직접 편집한다.** 이 영역이 본문의 유일한 원본(source of truth)이다. build.py는 재빌드 시 이
    영역을 페이지에서 도로 읽어 현재 템플릿으로 다시 감싸므로 직접 편집이 보존된다.
  - `_build/cases_src/{사례ID}_body.html`은 **신규 사례 최초 생성용 시드일 뿐**이다. 기존 사례의 본문을
    바꿀 때는 시드가 아니라 `cases/{사례ID}.html`을 고친다(시드는 낡아도 무방).
  - 메타데이터(제목·저자·쟁점·분류 등): `assets/meta.json` → 수정 후 `python3 _build/build.py`.
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
10. **원문 전체 보기 버튼은 같은 창으로 연다.** (규칙 3과 동일. `target="_blank"` 없이 생성 —
    build.py에 반영됨. PDF 내려받기 버튼은 다운로드이므로 `target="_blank"` 유지.)
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
assets/meta.json ─→ python3 _build/build.py ─→ index.html
                                            └─→ cases/{id}.html (chrome=템플릿, 본문=아래)

cases/{id}.html 의 <!-- BODY:START -->~<!-- BODY:END --> = 본문 원본(직접 편집)
   └─ build.py가 재빌드 시 이 영역을 도로 읽어 보존. cases_src는 신규 사례 시드로만 사용.
_build/cases_src/{id}_body.html ─(신규 사례 최초 1회만)─→ cases/{id}.html 본문 시드

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

### 기사 내용 수정 (오탈자, 문장, 그림 교체 등) — 저자 수정 요청 등 가장 흔한 작업
1. `cases/{id}.html`의 `<!-- BODY:START -->` ~ `<!-- BODY:END -->` 사이를 **직접 편집**한다.
   (원문 페이지도 바꿔야 하면 `fulltext/{id}/index.html`도 같이 직접 편집.) 사실관계는
   `_build/extract/{id}.txt`로 검증. 마커 밖(헤더·사이드바 등)은 건드리지 않는다 — 재빌드 시 덮어써진다.
2. 그림 교체 시 새 이미지를 `assets/img/{id}/`에 넣고 `../assets/img/{id}/파일명` 경로로 참조.
3. 본문만 고쳤다면 `build.py` 재실행은 **불필요**하다(페이지가 이미 최종본). 단 템플릿(헤더·푸터·
   사이드바·다운로드바)이나 `meta.json`을 함께 고쳤다면 `python3 _build/build.py`로 재빌드한다.
   재빌드해도 본문 직접 편집은 마커 덕분에 보존된다.
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
5. `python3 _build/build.py` → 검증 → 커밋. (첫 빌드가 `cases_src` 시드를 `cases/{id}.html`에
   심는다. 이후 이 사례의 본문 수정은 시드가 아니라 `cases/{id}.html`을 직접 고친다 — §4 "기사 내용 수정".)

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

## 6. 원문 전문(fulltext) 품질 개선 — 재추출 파이프라인 (2026-07 도입, 진행 중)

**현재 fulltext 본문 품질 작업의 표준 도구는 `_build/reextract_fulltext.py`다.** 구 gen_fulltext2.py
산출물의 구조적 결함(줄바꿈 띄어쓰기 누락·문장 분리, 각주 본문 흡수, 표 텍스트 잔존, 미주 무링크,
자동 크롭의 백지 이미지)을 **저장소 내 `pdf/{id}.pdf`에서 PyMuPDF로 본문을 재추출**해 근본 수정한다.
그림 이미지는 기존 `fulltext/{id}/img/*.webp`를 재사용(백지 자동 제거·대체)하므로 imgpool이 필요 없다.

- 실행(저장소 루트에서): `python _build/reextract_fulltext.py <사례ID>` → 해당 fulltext를 직접 갱신.
  `--dry`로 통계만 확인 가능. 상세 원리·새 사례 CONFIG 추가법은 스크립트 상단 docstring 참조.
- 의존성: `pip install PyMuPDF Pillow`. Windows 파이썬은 파일 IO에 utf-8 명시 필요(스크립트 반영됨).
- **파일별 CONFIG**(body_start·refs_head·table_pages, 필요시 body_size)를 스크립트의 `CFG`에 추가한다.
  파일마다 본문 시작 페이지·참고문헌 헤더·본문 폰트 크기·문단 들여쓰기·캡션 형식이 달라 육안 확인이 필수다.
- 절차: CONFIG 추가 → 실행 → `python -m http.server`로 육안 검증(그림 배치·표 잔존·띄어쓰기·미주 링크)
  → `git diff` 확인 → 사용자 검토 후 커밋.
- **진행 현황: 33편 완료·커밋**(260113·260111 파일럿 + 나머지 31편, CFG 등록 완료).
  - **재추출 제외 2편(기존 gen_fulltext2 유지)**: `240209`·`260105`는 삽화 텍스트가 많아 PyMuPDF가
    본문을 조각으로 읽어 문단이 폭발(재추출 부적합). CFG에 주석으로 남겨둠. 수동 실행 금지.
  - `210107`은 스캔본이라 애초에 이 파이프라인 대상 아님(gen_scanned 경로).
  - 즉 재추출 가능한 34편 중 33편 완료, 나머지는 위 특수 2편뿐.
- 알려진 한계: 그림 배치는 기존 HTML의 문단-그림 인접성 시그니처로 정렬하므로 드물게 어긋날 수 있음
  (육안 확인). 각주/미주 위첨자 감지가 휴리스틱이라 일부 앵커가 불일치할 수 있음(본문·참고문헌 텍스트는
  온전, 링크만 일부 안 걸림). 원문 자체 특이점(각주 1·2 동일 문구 등)은 사실 충실성 위해 그대로 반영.

구 방식(`gen_fulltext2.py`)은 아래 제약으로 **일반 유지보수에서 사용하지 않는다**(참고용 보존):

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
