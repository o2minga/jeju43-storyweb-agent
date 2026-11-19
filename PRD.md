# PRD — 제주 4·3 스토리웹 생성 AI 에이전트

> **문서 성격**: 기획문서 + `AGENT-SPEC.md` + 8개 스킬 정의서(`skills/01~08`) + 데이터 계약(`samples/*.json`)을 종합한 제품 요구사항 명세서.
> **읽는 법**: 이 문서는 "무엇을 만들 것인가(요구사항)"를 정의한다. "어떻게 판단·처리하는가(세부 규칙)"는 각 `skills/{번호}/spec.md`가 최종 근거다. 충돌 시 spec.md가 우선한다.
> **불변 원칙**: 결과물은 "웹페이지 한 장"이 아니라 **카드를 넣을 때마다 같은 품질의 페이지를 반복 생산하는 절차(에이전트·스킬) 그 자체**다. 어떤 유적지 카드가 들어와도 동일하게 동작해야 한다.

---

## 1. 프로젝트 개요 & 목적

### 1.1 한 줄 요약
유적지 카드(`.md`) 하나를 넣으면 → 검증 → 이야기 → 비주얼·오디오 → 인터랙티브 웹페이지 + AI 챗봇이 **자동으로** 생성되는, 반복 가능한 단일 AI 에이전트 파이프라인.

### 1.2 클라이언트 / 맥락
- 클라이언트: **함께공** × 제주대학교 AI융합원 부트캠프 (AX 실전 프로젝트)
- 소재: 제주 4·3 — **민감한 역사 소재**. 결과물 외부 공개 전 반드시 함께공과 상의.
- 평가 기준: "예쁜 정도"가 아니라 **기업(함께공) 요구사항 준수 여부**. 아래 가이드라인 위반이 가장 큰 감점.

### 1.3 목적 (Goal)
1. **반복성**: 카드만 교체하면 다음 장소도 동일 품질의 페이지가 나온다.
2. **신뢰성**: 검증된 사실만 노출하고, AI 연출물과 사실 기록을 명확히 구분한다.
3. **접근성**: 배경지식 없는 청소년·외국인이 이해할 수 있는 쉬운 언어.
4. **확장성**: 장소가 늘어나면 지도 인덱스에 핀만 추가되는 구조.

### 1.4 최종 산출물 (Deliverables)
| 산출물 | 형식 | 생성 스킬 |
|---|---|---|
| 장소별 스토리 웹페이지 | `.html` | 05-assemble |
| 지도 인덱스 (사이트 첫 화면) | `.html` | 06-map |
| 출처 대장 (함께공 감수·관리용) | `.md` | 08-review |
| 검수 결과 / 요약 | `.json` / `.md` | 08-review |
| 에이전트 & 스킬 워크플로우 가이드 | `.md` (= skills/ 8개 + 사용법) | 전체 |

---

## 2. 핵심 사용자 요구사항 & 가이드라인 준수 조건

### 2.1 5대 감점 방지선 (8개 스킬 전부 예외 없이 준수)
| # | 규칙 | 의미 | 기계 점검 지점 |
|---|---|---|---|
| 1 | **출처 표기 필수** | 카드 밖 자료 사용 가능하나 출처 명시. **개인 블로그·유튜브 금지**(공공기관·공식사이트·기사·논문·지도만) | 01, 08 |
| 2 | **쉬운 언어** | 청소년·외국인이 배경지식 없이 읽을 수 있게. 어려운 용어는 "용어 (쉬운 설명)"로 병기 | 02, 08 |
| 3 | **사실 vs 연출 구분** | AI 생성 이미지·영상·오디오에는 반드시 `[연출]` 표시. 기록 사진과 혼동 금지 | 03, 04, 05, 08 |
| 4 | **지어내기 금지** | 카드에 없는 내용(생사 여부, 발포 위치, 카드 밖 통설 등)은 절대 채우지 않음 | 01, 02, 07, 08 |
| 5 | **충돌 시 병기** | 자료마다 수치·날짜가 다르면 임의로 하나를 고르지 말고 "기록마다 다름"으로 나란히 표기 | 01, 02, 08 |

### 2.2 파생 필수 조건 (요구사항 상세)

#### (A) 재현 금지 게이트 — 03-visual 필수 관문
- 이미지·영상 생성 **전에 반드시 통과**. 폭력·피해·특정 인물 얼굴을 직접 재현하지 않는다.
- 감지 시 **직접 묘사를 폐기하고 상징으로 우회 변환**한 장면만 생성한다.

| 요청된(금지) 장면 | → 상징 우회 변환 |
|---|---|
| 총살·처형 | 텅 빈 광장, 흩어진 신발, 빈 의자 |
| 시신·피해자 | 흰 천 덮인 형체(신체 노출 없음), 놓인 꽃, 빈 자리 위의 빛 |
| 폭력·구타·연행 | 부서진 문, 늘어진 그림자, 빈 방 |
| 불타는 마을·방화 | 굴뚝만 남은 터, 식은 재, 무너진 돌담 |
| 총소리·발포 순간 | 인물 없는 공간, 흩어지는 새 |
| 특정 인물 얼굴 | 원경·뒷모습·실루엣, 얼굴 비특정 |

- **절대 금지(예외 없음)**: 잔인한 피해 장면 직접 묘사 / 실존 인물(피해자·생존자·가해자) 얼굴 복제. 우회로도 안 되면 **생성 포기** → 문헌 이미지 또는 상징으로 대체.

#### (B) `[연출]` 라벨 명시 규격
- AI 생성물: 출력 메타에 `is_ai_generated: true`, `label: "[연출]"`. 05는 `<figure class="ai-generated" data-origin="ai">` + `<figcaption>[연출] …</figcaption>`로 렌더.
- 문헌 이미지(실제 기록): `data-origin="archive"`, `[연출]` **미표시**, 출처 필수.
- AI 생성 이미지·영상·오디오는 **출처 대장(08)에서 제외** — 웹 내 `[연출]` 표시로만 관리.

#### (C) 출처 표기 규격
- 사실 문장은 05에서 `<span class="fact" data-fact-id="…" data-source="…">`로 감싼다. **출처 없는 사실 문장은 아예 조립하지 않는다.**
- 하단 `<footer class="sources">`에 출처 전체 표기.

#### (D) 공개 제한 플래그 (`publication_flag`)
- 01 → 02 → 05로 그대로 전달. `internal_only: true`이면 05가 `<head>`에 `<meta name="internal-only" content="true">` 삽입 → 08이 기계 확인.

#### (E) 정직한 부재 처리
- "정보가 없다/기록되지 않았다"는 서술 **자체가 검증된 사실**이다. 지어내기 금지 항목과 혼동해 누락하지 않는다.
- **conflict(자료마다 값이 다름 → 병기)** 와 **precision_guardrail(값은 하나인데 뭉뚱그리면 안 됨 → 정확 표현)** 은 별개 카테고리로 분리 처리.

#### (F) 챗봇(07) 외부 검색·출처 보강 정책 (Search & Grounding)
챗봇은 **내부 검증 사실(KB)을 우선**하되, 부족할 때만 **신뢰 출처 + 인용 조건 하에서** 외부 배경지식으로 보강할 수 있다. (기존 "KB 안에서만" 불변식의 통제된 확장 — 팀 공유 필요)
- **단계형**: ① 내부 KB(samples) → ② 외부 보강(큐레이션 `grounded` / 라이브 검색 provider) → ③ 폴백 "기록에 명시되지 않았습니다".
- **출처 의무**: 외부 보강 답변엔 `[출처: 기관, 사료명 / URL]` 명시. AI 가공·추론엔 `[AI 종합 연출 답변]` 라벨.
- **출처 채택 기준**: 신뢰도 있는 기관 자료는 **자유롭게** 사용 — 공공기관·공식 사료뿐 아니라 **검색·언론 기사**도 가능. 조건은 하나, **어디서 왔는지 출처를 남길 것.** 차단(denylist)은 **개인 블로그·유튜브** 및 이에 준하는 개인 UGC뿐. (참고 신뢰 출처: 제주4·3평화재단·국사편찬위원회·진실화해위원회·제주4·3연구소 등)
- **환각 금지(강제)**: 무출처이거나 인용이 전부 차단 대상(개인 블로그·유튜브)이면 답변 폐기 → 폴백. 민감·`forbidden_topics` 주제는 외부 검색조차 하지 않음. 외부 보강 결과는 함께공 감수 전 외부 공개 금지.
- **구현**: 라이브 웹검색은 서버(백엔드 Claude API + 웹 검색, 허용 도메인 한정)에서 수행하고, 정적 클라이언트(`js/chatbot.js`)는 `window.CHATBOT_GROUNDING` 훅으로 연결. 상세는 `skills/07-chatbot/SKILL.md` ④-보강.

---

## 3. 8개 스킬 파이프라인 흐름 & 데이터 전달 규격

### 3.1 스킬 그룹 (구현 방식별)
| 그룹 | 스킬 | 하는 일 | 구현 방식 | 현재 단계 |
|---|---|---|---|---|
| **A. 추론형** | 01, 02, 07, 08 | 텍스트 읽고 판단해 JSON 생성 | Claude API (SKILL.md가 지시문) | 실제 구현 |
| **B. 미디어 생성형** | 03, 04 | 이미지·영상·오디오 파일 생성 | 외부 API(Higgsfield·TTS) | **placeholder**(스키마만 확정, 내부 함수 후속 교체) |
| **C. 조립형** | 05, 06 | 데이터를 틀에 끼워 넣음 | 코드 템플릿(Claude 호출 없음) | A그룹 완료 후 |

### 3.2 실행 순서 (개발 순서와 다름)
```
01 검증 → 02 이야기 → 03 비주얼 → 04 오디오 → 07 챗봇 → 05 조립 → 06 지도 → 08 검수
```
- **07(챗봇)은 05(조립)보다 먼저** 완료된다 — 조립 시점에 완성된 모달을 끼워 넣기 위함.
- **06(지도)은 05 결과를 링크만** 하므로 마지막.

### 3.3 데이터 흐름
```
{아무}_카드.md
   └─▶ [01 검증] ──▶ 01-verify.json
          └─▶ [02 이야기] ──▶ 02-story.json ──┬─▶ [03 비주얼] ─▶ 03-visual.json (placeholder)
                                              ├─▶ [04 오디오] ─▶ 04-audio.json (placeholder)
                                              └─▶ [07 챗봇]   ─▶ 07-chatbot.json
                                                        │
   02·03·04·07 ─────────────────────────────▶ [05 조립] ─▶ output/{id}/index.html
                                                        └─▶ [06 지도] ─▶ output/index.html
                                                        └─▶ [08 검수] ─▶ review_result.json + source-ledger.md + review-summary.md
```

### 3.4 스킬별 입출력 규격 (계약)
> 계약의 실제 스키마는 `samples/*.json` 및 각 `spec.md` 6장이 근거. 아래는 요약.

| # | 스킬 | 입력 | 출력(계약 파일) | 핵심 필드 |
|---|---|---|---|---|
| 01 | verify(문지기) | 카드 `.md` | `01-verify.json` | `verified_facts` · `sources` · `forbidden_topics` · `conflicts` · `precision_guardrails` · `verbatim_quotes` · `publication_flag` |
| 02 | story(번역가) | `01-verify.json` + 카드 | `02-story.json` / `samples/02-story-output-example.json` | `story{intro,development,closing}` · `sources_by_sentence` · `forbidden_topics` · `conflicts_carried_forward` · `precision_guardrails_applied` · `image_prompts_draft` · `timeline_events` · `chatbot_kb` · `target_mode` · `publication_flag` |
| 03 | visual(미술감독) | 02의 `image_prompts_draft` | `03-visual.json` / `samples/03-visual-output-example.json` | `assets[]{asset_id,source_prompt_id,type,path,is_ai_generated,label,gate,gate_reason,source,caption}` · `gate_summary` |
| 04 | audio(음향감독) | 02의 `story` · `timeline_events` | `04-audio.json` / `samples/04-audio-output-example.json` | `narration` · `bgm` · `pronunciation_dict` · `sync_timeline` · `web_asset_package` |
| 07 | chatbot(안내원) | 02의 `chatbot_kb` + 01의 `forbidden_topics` | `07-chatbot.json` / `samples/07-chatbot-output-example.json` | `kb[]` · `guardrail{system_prompt,fallback_answer,refuse_topics,conflict_note}` · `widget{launcher,modal_script_path}` |
| 05 | assemble(조립공) | 02·03·04·07 출력 | `output/{id}/index.html` | (마크업 규칙 → §4.5) |
| 06 | map(현관문) | 여러 장소의 05 결과 목록 | `output/index.html` / `samples/06-map-input-example.json` | `map{image,width_px,height_px,bounds}` · `places[]{location_id,name,coord,one_liner,thumbnail,page_link}` |
| 08 | review(감수관) | 01·02·07 JSON + 05 html (+03·04·06) | `review_result.json` · `source-ledger.md` · `review-summary.md` | `overall_status(PASS/HOLD/실행불가)` · `checks[]` |

### 3.5 언어 라벨 규약
- 모든 텍스트 필드는 `{ "ko": "…", "en": "" }` 구조. **이번 단계는 `ko`만 채우고 `en`은 빈 문자열로 자리만 유지**(02 영어 대본 완성 후 대응).

### 3.6 방어적 처리 (공통)
- 입력 섹션/배열이 없으면 **빈 값으로 두고 지어내지 않는다**. (예: `image_prompts_draft` 없음 → `assets: []`, `chatbot_kb` 없음 → 모든 질문 fallback, `timeline_events` 없음 → 05가 타임라인 블록 자체를 생략)

---

## 4. 최종 결과물 UI/UX 요구사항 (05-assemble 출력 웹페이지)

> 원칙: **세로 스크롤형 단일 `.html`**, 블록을 내용에 맞게 골라 쌓음. **해당 데이터가 없는 블록은 자동 생략**(빈 블록을 숨기는 게 아니라 애초에 생성하지 않음). 스타일은 별도 `design` 파일로 분리 → **파일 교체만으로 전체 톤 변경**, 없으면 무채색 최소 스타일로 fallback.

### 4.1 세로 스크롤 레이아웃 구조

| 섹션 | 역할 | 데이터 소스 | 없을 때 |
|---|---|---|---|
| **Hero** | 장소명 + 대표 비주얼 + 한 줄 성격 | `location_name` + 03 대표 asset(현재 시점 이미지 권장) | 비주얼 없으면(placeholder) "준비 중" 표시, 텍스트만으로 렌더 |
| **Intro** | 도입 — 왜 이곳이 특별한지 궁금증 유발 | `story.intro.ko` | 필수(02 없으면 조립 중단) |
| **Body** | 전개 — 무슨 일이 있었나 (사실+맥락) | `story.development.ko` + 본문 중간 03 비주얼 + 04 오디오 플레이어 | 비주얼/오디오 placeholder면 해당 요소만 생략/준비중 |
| **Timeline** | 인터랙티브 연표 | `timeline_events[]` | 이벤트 없으면 **블록 전체 생략** |
| **Outro** | 마무리 — 현재적 의미로 왜 기억되는가 | `story.closing.ko` | 필수 |
| **Footer** | 출처 목록 + 공개 제한 메타 | `sources_by_sentence` + `publication_flag` | 출처 없는 사실은 애초 미노출 |

- **읽기 흐름**: Hero(몰입) → Intro(궁금증) → Body(사실+비주얼+오디오) → Timeline(시간축 정리) → Outro(의미) → Footer(근거). 스크롤 진행에 따라 섹션이 자연스럽게 전개.
- **접근성**: 어려운 용어는 본문에서 "용어 (쉬운 설명)"로 병기(02 산출). 이미지 `alt`, 오디오 대체 텍스트 제공.

### 4.2 오디오 플레이어 & Visual 에셋 매핑

**오디오 플레이어 (04-audio → Body 내 배치)**
- `narration.path`(TTS ko)를 메인 트랙, `bgm.path`를 낮은 음량(`volume_relative_to_narration` ≈ 0.25)으로 겹쳐 재생.
- `sync_timeline[]`(intro/development/closing 문단 단위 `start_sec`~`end_sec`)로 **재생 위치에 맞춰 현재 문단 하이라이트** 가능.
- `narration`은 AI 생성물 → 플레이어 영역에 생성 표기.
- placeholder 단계면 플레이어 자리에 "오디오 준비 중" 표시(조립은 계속).

**Visual 에셋 매핑 (03-visual → Hero/Body 배치)**
- 각 `asset`의 `source_prompt_id`(=02의 `image_prompts_draft.prompt_id`)로 **해당 장면 위치에 배치**.
- `type`: `image` / `video`(짧은 숏폼) / `archival`(문헌).
- 렌더 규칙:
  - AI 생성(`is_ai_generated:true`) → `<figure class="ai-generated" data-origin="ai">` + `<figcaption>[연출] {caption}</figcaption>`
  - 문헌(`type:"archival"`) → `data-origin="archive"`, `[연출]` 없음, 출처 캡션 필수
- `gate:"skipped"` 자산은 배치하지 않고 대체 자산으로 대신한다.

### 4.3 우측 하단 Floating 챗봇 모달 UI 규격 (07-chatbot)
- **런처**: `widget.launcher = "floating-bottom-right"` — 우측 하단 고정 floating 버튼. 스크롤과 무관하게 항상 노출.
- **모달**: 버튼 클릭 → 우측 하단에서 채팅 모달 오픈. 05는 `<div id="chatbot-modal" data-kb-source="07">`로 삽입(자기완결 스크립트, 외부 라이브러리 의존 없음).
- **동작 규격(가드레일)**:
  - 질문을 `kb[].question`/`tags`와 매칭 → 매칭 시 `answer`(+ `source`).
  - 미매칭 또는 `refuse_topics` 해당 → `guardrail.fallback_answer` = **"기록에 명시되지 않은 내용입니다."**
  - 충돌 사실은 "기록마다 다름"으로 병기. 정치 편향·주관 논평·과장된 감정 이입 금지.
- **표시**: 챗봇 답변은 검증된 KB 기반임을 안내(예: 근거 출처 노출). 창작·추측 문구 노출 금지.

### 4.4 톤 & 비주얼 아이덴티티 (design 파일 기준)
- 차분한 다큐멘터리 톤, **저채도**(선명한 빨강·네온 금지 — 유혈 연상 차단), 차가운 회청색·바랜 세피아, 흐린 아침빛, 넉넉한 여백(부재·애도의 언어). (상세: `skills/03-visual/art-style.md`)
- 과거 장면은 세피아 기운, 현재 장면은 차가운 무채색으로 **과거-현재를 색으로 구분**.

### 4.5 HTML 마크업 규칙 (⚠ 08-review 자동 검수가 의존 — 임의 변경 금지)
```html
<!-- 사실 문장 -->
<span class="fact" data-fact-id="{02의 sentence_id/fact_id}" data-source="{출처명}">…</span>

<!-- AI 생성물 [연출] -->
<figure class="ai-generated" data-origin="ai"><img src="…" alt="…"><figcaption>[연출] …</figcaption></figure>
<!-- 문헌 이미지 -->
<figure data-origin="archive"><img src="…" alt="…"><figcaption>{출처}</figcaption></figure>

<!-- 타임라인 -->
<div class="timeline-event" data-event-id="{02의 event_id}">…</div>

<!-- 챗봇 모달 -->
<div id="chatbot-modal" data-kb-source="07">…</div>

<!-- 출처 하단 -->
<footer class="sources"><ul><li data-source-ref="{출처명}">{출처 전체 표기}</li></ul></footer>

<!-- 공개 제한(있을 때) -->
<meta name="internal-only" content="true">
```
> 새 블록이 필요하면 **`skills/05-assemble/spec.md`에 규칙을 먼저 추가한 뒤** 구현한다(문서에 없는 태그는 08이 검수 못 함).

---

## 5. 단계별 개발 / 검증 체크리스트

> 스킬 완성 직후 **관덕정 카드로 실제 한 바퀴** 돌려 팀이 함께 즉시 테스트한다(스킬 자체 검수). 별도 문서가 아니라 제작 직후 바로 실행.

### Phase 1 — 데이터 스키마 확정 (계약 우선)
- [ ] `AGENT-SPEC.md` 카드 표준 구조 / 출처 3패턴 확정
- [ ] `samples/*.json` 스키마 확정 (01·02·03·04·07 계약 + 06 입력) — **키 이름이 곧 인터페이스 계약**
- [ ] 02 출력이 03·04·07의 입력과 정합(키 이름·구조 일치) — 변경 시 즉시 상대에게 통지
- [ ] 언어 라벨 `{ko,en}` 구조 전 필드 적용, `publication_flag` 전달 경로(01→02→05) 확인
- [ ] conflict vs precision_guardrail 분리 표현 확정

### Phase 2 — 스킬 개별 동작 (단위 검증)
- [ ] **01**: 카드 방어적 파싱, 모든 사실에 출처 매칭, 금지 목록 원문 보존, 충돌/정밀도 분리
- [ ] **02**: 쉬운 언어·용어 풀이, forbidden 미준수 0, conflicts 병기, 타임라인/KB 추출, 가드레일 테스트 질문 ≥1
- [ ] **03**: 재현 금지 게이트 통과(우회 0건 누락), 실존 인물 얼굴 0건, 문헌 우선, art-style 자동 첨부, 전 자산 `[연출]`
- [ ] **04**: 차분 톤, 발음 사전 적용, 로열티프리/자체 BGM(출처 표기), 밸런싱, 싱크 타임라인
- [ ] **07**: KB 내 답변, KB 밖·금지주제 100% fallback, 중립, floating 모달 구동
- [ ] **06**: 좌표→픽셀 변환 정확, 줌/팬에도 핀 고정, 카드 추가만으로 핀 증가, 오프라인 동작
- [ ] 각 스킬을 **다른 유적지 카드로도** 실행해 일반화 확인(특정 장소 하드코딩 없음)

### Phase 3 — 최종 조립 및 검수 (통합 검증)
- [ ] **05**: 세로 스크롤 6섹션(Hero/Intro/Body/Timeline/Outro/Footer) 조립, 없는 블록 자동 생략
- [ ] 05: 사실 문장 전부 `data-source` 부착, AI 생성물 `[연출]`+`class="ai-generated"`, `internal-only` 메타(해당 시)
- [ ] 05: 03·04 placeholder여도 에러 없이 "준비 중"으로 완주, design 파일 교체로 톤 변경
- [ ] 05: 오디오 플레이어(narration+bgm+싱크), floating 챗봇 모달 정상 연동
- [ ] **06**: 여러 장소 인덱스에서 핀 클릭 → 해당 05 페이지 이동
- [ ] **08**: 필수 파일(01·02·07 json + 05 html) 존재 확인, 6개 항목 모두 pass/fail/needs_human/blocked로 귀결
- [ ] 08: `needs_human` 있으면 overall = HOLD, 출처 대장에 AI 생성물 미포함, 동일 입력 동일 결과(재현성)
- [ ] **통합**: 관덕정 카드 1장으로 01→08 전체 파이프라인 무중단 완주, 결과 사람 확인
- [ ] 공개 전 **함께공과 상의** (민감 소재)

---

## 부록 A. 폴더 구조
```
jeju43-storyweb-agent/
├── PRD.md                      ← 이 문서
├── AGENT-SPEC.md               ← 전체 아키텍처
├── skills/{01~08}/SKILL.md · spec.md   ← 실행 지시문 + 상세 설계
├── samples/*.json              ← 스킬 간 데이터 계약(더미)
├── test-card/관덕정_카드.md      ← 공용 테스트 카드(예시일 뿐, 기준 아님)
├── output/{location_id}/       ← 카드 1장당 결과 폴더(실행 시 덮어씀)
└── docs/jeju43-agent_팀작업가이드.md
```

## 부록 B. 환경 변수
```
ANTHROPIC_API_KEY=            # A그룹(01·02·07·08) 실제 동작
HIGGSFIELD_API_KEY=          # 03 — placeholder 단계, 후속
TTS_API_KEY=                 # 04 — placeholder 단계, 후속
# Supabase(선택, 저장/인증용): NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY / SUPABASE_SERVICE_ROLE_KEY
```

## 부록 C. 역할 분담
- **박이현 (A) — 뼈대(데이터 흐름)**: 01-verify · 02-story · 05-assemble · 08-review
- **백민하 (B) — 멀티미디어·인터랙션**: 03-visual · 04-audio · 06-map · 07-chatbot
- 브랜치는 스킬 단위(`feature/01-verify` ~ `feature/08-review`). 한 스킬 끝나면 바로 PR → merge.
- **충돌 주의 파일**(수정 전 상대에게 통지): `samples/*.json` · `test-card/관덕정_카드.md` · `CLAUDE.md` · `README.md` · 본 `PRD.md`
