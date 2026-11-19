---
name: 05-assemble
description: 02(이야기)·03(비주얼)·04(오디오)·07(챗봇)의 출력이 준비되어 있고(03·04는 placeholder여도 무방), 이를 하나의 브라우저 스토리 웹페이지(.html)로 조립해야 할 때 사용한다. 특정 유적지에 종속되지 않고 어떤 장소의 산출물이 들어와도 동일하게 동작해야 한다.
---

# 웹페이지 조립 스킬 ‹조립공›

> 상세 설계는 `skills/05-assemble/spec.md`, 전체 구조는 `AGENT-SPEC.md` 참고. 이 문서는 그 두 문서를 바탕으로 한 실행 지시문이며, **특정 유적지의 실제 내용은 예시로도 포함하지 않는다.**
> ⚠ 출력 마크업 규칙(spec.md 5장)은 08-review가 자동 검수할 수 있는 유일한 근거다. 여기 정의된 태그·속성 구조를 임의로 바꾸지 않는다.

## ① 목표
02·03·04·07의 결과물을 받아, 브라우저에서 열리는 스토리 웹페이지(`.html`) 한 장으로 조립한다. 카드만 바꿔 넣으면 같은 품질의 페이지가 나오는 **반복성**을 담보하는 자리다.

## ② 맥락
02, 07 출력은 필수 입력이다 — 없으면 조립을 중단한다. 03·04는 아직 placeholder 단계일 수 있으며, 이 경우 해당 블록을 "준비 중" 상태로 표시하고 조립은 계속 진행한다(placeholder라는 이유로 실패 처리하지 않는다 — 개발 초기엔 이게 정상 상태다). 07 출력이 없으면 챗봇 블록만 정상적으로 생략한다(에러 아님).
- (구현 메모) 아이보리 리디자인(지도로 돌아가기 nav·EN/KO 언어 토글·`output/design/archive.css` 연결·히어로 이미지·이중언어 렌더링·실제 sync_timeline 기반 낭독 하이라이트)은 `step05_assemble.py`가 직접 생성한다 — 원래 사람이 관덕정·곤을동·너븐숭이 페이지에 손으로만 적용해서, 코드로 재조립하면 예전 단순 스타일로 되돌아가는 문제가 있었다(`PROGRESS.md` 참고). 다만 "이야기 확인 퀴즈" 섹션과 영문 문단 안의 문장 단위 "[Source: ...]" 인용은 스키마에 데이터로 없는 손 작업이라 코드가 만들지 않는다 — 필요하면 02(퀴즈 필드+생성 로직) 쪽에 별도 기능으로 추가해야 한다.

## ③ 범위 (포함 / 제외)
**포함**
- 원고를 화면 구획에 배치, 내용에 맞는 블록 선택·조립
- 출처를 규칙대로 하단에 표기
- 사실 서술과 `[연출]` 표시 구분 렌더링
- 인터랙티브 타임라인, AI 챗봇 모달 스크립트 연동
- `.html` 파일 출력

**제외**
- 이야기 창작(02), 이미지·영상 생성(03), 오디오 생성(04), 챗봇 스크립트 개발(07)
- 여러 장소를 지도로 묶는 일(06 담당)

## ④ 제약
- 기본 틀은 세로 스크롤형. 블록(글·타임라인·인용·이미지·영상·오디오 플레이어·출처)을 내용에 맞게 골라 쌓는다.
- **없는 요소의 블록은 자동 생략한다** — 빈 블록을 만들고 숨기는 게 아니라, 애초에 생성하지 않는다.
- 스타일은 별도 `design` 파일로 분리한다. `.html` 본문에 스타일을 하드코딩하지 않으며, design 파일 교체만으로 전체 톤이 바뀌어야 한다. design 파일이 없으면 기본(무채색 최소 스타일)으로 fallback한다.
- `publication_flag.internal_only`가 `true`이면 완성된 `.html`의 `<head>`에 `<meta name="internal-only" content="true">`를 **반드시** 삽입한다 — 08이 기계적으로 확인하는 유일한 방법이므로 누락 금지.
- 출처가 없는 사실 문장은 애초에 `fact` 태그로 감싸 조립하지 않는다(출처 없이 화면에 노출되는 사실이 없어야 함).
- 조립 시점에 02·07 산출물은 반드시 준비되어 있어야 한다(03·04는 placeholder 허용).

## ⑤ 출력 형식 (마크업 규칙 — spec.md 5장을 그대로 따름, 임의 변경 금지)
`skills/05-assemble/spec.md` 5장에 정의된 태그·속성 구조를 그대로 사용한다.

- 사실 문장: `<span class="fact" data-fact-id="..." data-source="...">`
- AI 생성물: `<figure class="ai-generated" data-origin="ai">` + `[연출]`이 포함된 `<figcaption>`. 문헌 원본은 `data-origin="archive"`(class="ai-generated" 미부착)
- 타임라인: `<div class="timeline-event" data-event-id="...">`
- 챗봇 모달: `<div id="chatbot-modal" data-kb-source="07">`
- 출처 하단: `<footer class="sources">` 안에 `data-source-ref`를 가진 목록

이 규칙에 없는 새 블록이 필요하면 **spec.md에 규칙을 먼저 추가한 뒤 구현한다** — 문서에 없는 태그 구조로 조립하면 08이 검수를 못 하거나 잘못된 결과를 낸다.

## ⑥ 성공 기준
`skills/05-assemble/spec.md` 7장의 체크리스트를 그대로 따른다. 특히 아래는 항상 확인한다.
- 카드만 바꿔 넣으면 다음 장소도 같은 품질의 페이지가 나온다(반복성).
- 모든 사실 문장이 `data-source`를 가진 `fact` 태그로 감싸져 있다.
- 모든 AI 생성 이미지·영상에 `[연출]` 캡션과 `class="ai-generated"`가 붙어 있다.
- `publication_flag.internal_only`가 true인 경우 `<meta name="internal-only">`가 삽입되어 있다.
- 03·04가 placeholder 상태여도 조립이 에러 없이 완료된다.
- design 파일 교체만으로 전체 톤이 바뀐다.
- **이 스킬을 다른 유적지의 02·03·04·07 출력으로 실행해도 동일한 기준을 만족한다.**

## 공통 규칙 (모든 스킬 공통)
1. **출처 표기 필수** — 카드 밖 자료도 가능하나 출처 명시. 개인 블로그·유튜브 금지
2. **쉬운 언어** — 청소년·외국인이 배경지식 없이 읽을 수 있게
3. **사실 vs 연출 구분** — AI 생성 이미지·영상엔 `[연출]` 표시
4. **지어내기 금지** — 카드에 없는 내용은 채우지 않음
5. **충돌 시 병기** — 수치·날짜가 자료마다 다르면 '기록마다 다름'으로 나란히 표기

## 입력 예시 / 출력 예시
- 입력 예시: `output/gwandeokjeong/02-story.json`, `samples/03-visual-output-example.json`/`samples/04-audio-output-example.json`(placeholder 대체용), `samples/07-chatbot-output-example.json`
- 출력 예시: `output/gwandeokjeong/05-assemble.html` (아직 미작성 — 실행 테스트 시 생성)

---

# 부록 A. 웹앱(index/story/챗봇) ↔ samples 연동 지침

`skills/05-assemble/` 안의 실제 웹앱(백민하 제작)을 파이프라인 `samples/*.json`에 연결하는 방법. **기존 디자인/JS(app.js·story.js·chatbot.js·glossary.js·md-parser.js·reveal.js·i18n.js)는 한 줄도 수정하지 않는다.** 연결은 어댑터 한 개(`js/pipeline-adapter.js`)로만 한다.

## A-1. 파일 구성
```
skills/05-assemble/
├── index.html      ← 지도+카드 인덱스 (Leaflet). data/sites.json 소비
├── story.html      ← 스토리 상세. ?site=<id> → data/<id>.json 소비  (이번에 신규 생성)
├── css/style.css   ← 토큰(:root)+인덱스 스타일 / css/story.css ← 스토리 컴포넌트
├── js/
│   ├── pipeline-adapter.js  ← ★ samples → 앱 계약 어댑터 (fetch shim). 다른 JS보다 먼저 로드
│   ├── i18n.js·glossary.js·reveal.js·app.js·story.js·chatbot.js·md-parser.js  ← 원본 유지
└── SKILL.md·spec.md
```

## A-2. 어댑터 동작 (`js/pipeline-adapter.js`)
`window.fetch`를 감싸(shim), 앱이 원래 요청하는 3개 URL을 가로채 samples를 앱 스키마로 변환해 응답한다. 그 외 요청(지도 타일 등)은 그대로 통과. samples는 앱 HTML 기준 상대경로 `../../samples/`에서 읽는다.

| 앱이 요청하는 URL | 어댑터가 변환에 쓰는 samples | 앱 스키마 |
|---|---|---|
| `data/sites.json` | 06(장소 목록) + 02(장소명) | `{sites:[{id,lat,lng,name,summary,region,kind,story}]}` |
| `data/<id>.json` | 02(이야기·타임라인·출처·병기·플래그) + 03(비주얼) + 04(오디오) | `{hero,sections[{kicker,heading,blocks}],sources,notice}` |
| `data/chatbot-kb.json` | 07(KB·가드레일) | `{persona,sensitive,entries,fallback}` |

## A-3. 공통 규칙(감점 방지선) 렌더링 매핑 — 점검 완료
- **[연출]/AI 표기**: 03 asset → story `media.flag`. `gate:"converted"`(재현금지 우회)→`연출` 배지, 그 외 `is_ai_generated`→`ai`("AI 생성") 배지, `type:"archival"`(문헌)→배지 없이 `credit`(출처)만. → story.js `badgeHtml()` 그대로 사용. (푸터 범례가 두 표기를 설명)
- **출처 표기**: 문장 `source`→`〔출처〕`(story.js `srcTag`), 하단 `sources` 목록, 챗봇 답변 뒤 `〔출처〕`. **AI 생성물은 출처 대장/목록에 넣지 않음**(웹 내 배지로만 관리 — 08 규칙과 일치).
- **용어 풀이(glossary)**: 하드코딩 사전(`glossary.js`)이 렌더된 본문을 자동 스캔해 `.gloss` 툴팁 부여(예 "4·3"). 추가 용어는 `glossary.js`에만 넣는다.
- **지어내기 금지**: samples에 없는 값은 채우지 않음. `region`은 섬 단위 `'제주'`로만 둠(좌표 밖 지역명 임의 생성 금지).
- **충돌 병기**: `conflicts_carried_forward`→`diff`("⚖️ 기록마다 다릅니다"), `precision_guardrails_applied`→`note`("단정하지 않았습니다").
- **⚠ 오디오**: 현재 story.js에 오디오 블록 렌더러가 없음(구조 유지 원칙상 추가하지 않음) → 04는 `note` 블록으로 "낭독 오디오 제공(AI 생성 표기 대상)"만 안내. 실제 플레이어가 필요하면 story.js에 `case 'audio'` 렌더러를 spec.md 5장에 규칙 추가 후 확장한다.

## A-4. 실행
저장소 **루트**를 서빙해야 `../../samples/`가 도달 가능하다.
```
node scripts/serve.mjs . 8003
# → http://localhost:8003/skills/05-assemble/index.html
```
지도 핀/카드 → `story.html?site=gwandeokjeong` → 어댑터가 02·03·04를 스토리로 렌더. 우측 하단 챗봇 '동백'은 07 KB 안에서만 답하고, 없는 질문·민감 질문은 "기록에 명시되지 않았습니다"로 폴백.

## A-5. 확장 (다른 유적지/실데이터)
- 실제 파이프라인 연결 시: 어댑터의 `FILES` 경로를 각 장소의 `output/<id>/0X-*.json`으로 바꾸거나, 카드별로 samples를 교체. 앱 스키마(위 표)만 지키면 렌더 코드는 그대로 재사용된다.
- 여러 장소: 06 입력의 `places[]`에 항목을 추가하면 인덱스 핀·카드가 자동 증가(각 장소의 02/03/04가 있어야 스토리 렌더).
- 이미지 실파일이 생기면 `path`가 `http(s):`/`data:`거나 접근 가능한 경로일 때 자동 표시되고, 없으면 상징 플레이스홀더로 폴백한다.
