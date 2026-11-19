# PROGRESS

> ⚠️ **세션을 새로 시작할 때마다 이 파일을 가장 먼저 확인할 것.** 지금까지 뭐가 끝났고,
> 뭐가 진행 중이고, 뭐가 아직 손도 안 댔는지, 그리고 다음에 뭘 최우선으로 확인해야
> 하는지가 여기 정리돼 있다.

## 문서

- [x] CLAUDE.md — 프로젝트 개요·5대 공통 규칙·8스킬 구조·팀 역할 분담
- [x] AGENT-SPEC.md — 전체 흐름·3그룹(A/B/C) 아키텍처·실행 순서
- [x] `skills/01-verify` ~ `skills/08-review` — 8개 스킬 전부 SKILL.md + spec.md 작성 완료
- [x] `docs/jeju43-agent_팀작업가이드.md` — 팀 작업 방식·스키마 계약·브랜치 전략
- [x] PRD.md — 05-assemble 웹앱 관련 제품 요구사항 정리

## 하네스-검증

- [x] `agent/schema/` — 01~08 각 스텝 출력 스키마를 Pydantic 모델로 구현(01의
      conflicts/precision_guardrails는 키 자체가 항상 존재하도록 강제)
- [x] `agent/schema/validate.py` — step_id만 알면 JSON/HTML 산출물을 알맞은 모델로
      검증해주는 단일 진입점
- [x] `agent/run_agent.py` — 01→02→03→04→07→05→06→08 순서로 스텝별 생성 직후 검증,
      실패 시 어느 스텝·어느 필드가 문제인지 출력하고 중단
- [x] 08-review — ①②④⑥은 코드 파싱(재현성 확보), ③만 Claude 판단, ⑤는 고정
      `needs_human`으로 리팩토링 완료(회귀 테스트로 확인)
- [x] 05-assemble — 02의 문장이 문단에 매칭 안 되면 조용히 넘어가던 걸 진단 마커 +
      검증 fail로 수정
- [x] 관덕정 카드로 03~08 전체 파이프라인 실행 테스트 완료(실제 산출물 생성, 검증 통과)
- [x] Group B(03-visual/04-audio) placeholder 게이트 로직 구현·테스트
      (실제 Higgsfield/TTS 키 생기면 내부만 교체하면 되는 구조)
- [x] **03-visual/04-audio placeholder 실제 생성으로 교체 완료** — 03은 Cloudflare
      Workers AI(flux-1-schnell, `agent/generate/image_backend.py`), 04는 Windows
      SAPI(TTS) + numpy 절차적 합성(BGM, `agent/generate/audio_backend.py`)으로 실제
      파일을 생성한다. 실제 API 호출·산출물 검증까지 완료(스킬 상세는
      `skills/03-visual/SKILL.md`/`skills/04-audio/SKILL.md` 참고).

## 하네스-재시도로깅 (완료)

`agent/llm_client.py` 안에서 실제로 도는 재시도·로깅 — Python `logging`으로 stdout에
남는다. 실행해서 직접 확인함(존재 여부 검증 완료):
- [x] `call_model()` — provider 분기, JSON 파싱 실패 시 재시도, 매 시도 성공/실패 로그
- [x] `generate_validated()` — pydantic 검증 실패 이유를 프롬프트에 되먹여 재시도, 시도
      번호·성공/실패 로그
- [x] `generate_validated_with_tools()` — tool_use 호출 여부·모델이 남긴 판단 이유·
      handler 실행 결과까지 로그로 남김(bounded_search 몽키패치 테스트로 확인)

## 하네스-데모진행로그 (완료)

`feature/harness-logging`에서 구현·실행 테스트까지 마침(관덕정 카드로 실제 실행해
터미널 출력과 로그 파일 생성을 직접 확인함):
- [x] `run_agent.py` 실행 시 `[01/8] 자료 검증 시작...` → `[01/8] 완료 — 사실 N건,
      출처 N건 확인됨` 같은, 스텝마다 다른 내용의 사람이 보기 좋은 8단계 진행 표시
      (실행 순서 기준 번호 — `--resume-from`으로 중간부터 시작해도 전체 8단계 중
      몇 번째인지 정확히 보여줌)
- [x] `logs/{location_id}/{실행시각}/steps.jsonl` — 스텝별 시각·시도 횟수·프롬프트/
      응답 요약·토큰 수·소요시간·검증 결과·에러 메시지를 한 줄씩 기록. LLM을 실제로
      부르지 않은 스텝(결정론적 03/04/05/06, 또는 파일을 재사용해 이번 실행엔 호출이
      없었던 01/02/07/08)은 값 대신 "규칙 기반 생성 — LLM 호출 없음" 등 이유가 남아
      이전 스텝 수치가 새어 들어간 것처럼 보이지 않는다
- [x] `logs/{location_id}/{실행시각}/run-summary.json` — 총 소요시간·총 입출력 토큰·
      스텝별 최종 상태·재시도 발생 여부 요약
- [ ] ⚠ 위 텔레메트리(토큰 수·시도 횟수) 배관은 실제 `ANTHROPIC_API_KEY`가 없는
      환경에서 구현·라우팅만 확인했다 — 실제 LLM 호출이 발생했을 때 토큰 수치가
      제대로 채워지는지는 키가 생기면 최우선으로 재확인 필요

## Supabase

- [x] `supabase/schema.sql` — `locations` 테이블(location_id/detail_html/map_html/
      updated_at), RLS 켜고 anon/authenticated 정책 없음(service_role 전용)
- [x] `agent/generate/step05_assemble.py`의 `sync_to_supabase()` — 05 스텝이 끝날 때마다
      최신 map_html과 함께 upsert(키 없으면 경고만, 있는데 실패하면 에러)
- [x] 팀·함께공 전용 비공개 미리보기 — `src/proxy.ts`(사이트 전체 비밀번호 게이트),
      `/preview-login`, `/api/preview/{detail,map}`(service_role 키로 서버에서만 조회)
- [x] 실제 Supabase 프로젝트에 연결해 `gwandeokjeong` row가 진짜로 생성됨을 재조회로 확인
- [ ] 01/02/07/08까지 포함한 **실제 API 키로의 풀 파이프라인 → Supabase 동기화**는
      아직 미검증(지금까지는 05/06 결정론적 스텝만 실제로 태워봄)

## 에이전트화

- [x] `agent/agents/base.py` — `Agent` 기본 클래스(name/skill_md_path/tools/output_schema,
      `run()`이 generate_validated 호출을 흡수)
- [x] 01/02/07/08을 각각 `VerifyAgent`/`StoryAgent`/`ChatbotAgent`/`ReviewAgent`로 리팩토링
      — `git stash` 전후 비교로 동작 무변경 확인(SHA256 완전 일치)
- [x] `agent/subagents/bounded_search.py` — VerifyAgent에 tool로 등록, 모델이 스스로
      호출 여부 판단(강제 호출 아님). Mock 기반으로 라우팅(호출 여부·handler 실행·
      최종 검증)까지는 확인함
- [ ] ⚠ **API 키 생기면 최우선 확인**: `tools` + `output_config.format`(구조화 출력)이
      실제 Anthropic API에서 함께 작동하는지. `agent/llm_client.py`의
      `generate_validated_with_tools()`가 문서로 확인 못 하고 가정만 하고 구현한 부분.
      안 되면 tool 응답을 받은 후 별도로 구조화 출력을 한 번 더 요청하는 2단계 호출
      방식으로 바꿔야 할 수 있음

## 파이프라인 훅(Hook) 시스템

- [x] `agent/hooks/` — Flask의 before/after_request, Django의 signal과 같은 콜백
      레지스트리(순수 dict/list, 외부 라이브러리 불필요). `run_agent.py`가
      `before_step`/`after_step`/`on_complete` 세 시점에서 `fire()`를 호출하고, 콜백
      하나가 예외를 던져도 파이프라인은 멈추지 않는다(경고 로그만 남김)
- [x] `hooks/human_report.py` — on_complete에서 08 결과를 훅의 구조적 status가 아니라
      `result.overall_status`/`checks[].status`를 직접 읽어 판정해 사람이 읽는
      `human-review-report.md`를 생성한다(HOLD·needs_human을 "정상 완료"로 오인하는
      함정을 피함 — gwandeokjeong 실제 실행으로 확인)
- [x] `hooks/supabase_sync.py` — after_step("05")에서 실제 HTML 원문을 Supabase
      locations 테이블에 동기화. dispatch.py의 05 생성 경로에 있던 인라인 동기화
      호출은 제거하고 이 훅 하나로 일원화(재생성·재사용 두 경우 모두 정확히 1회만
      동기화되는 것을 실제로 확인)
- [x] **`asset_override`는 별도 훅 파일로 만들지 않았다** — 대신 `visual_agent.py`의
      이미지 확보 우선순위를 "Cloudflare 먼저 → 관리자 지정 파일"에서 "관리자 지정
      파일 먼저 → (없을 때만) Cloudflare"로 바꾸는 것으로 같은 목적을 달성했다.
      이유(한 줄): 훅 시스템이 03의 실행 흐름에 개입할 통로가 없어서
      (`hooks.fire("before_step")`의 반환값을 dispatch.py 어디서도 확인하지 않음).
- [x] **04-audio도 같은 문제가 있어 같은 방식으로 고침** — 확인해보니 04는 03보다도
      기본적인 상태였다(관리자 지정 경로 자체가 아예 없이 "output에 이미 있으면
      재사용 → 없으면 곧장 SAPI/numpy 자동 합성"뿐이었음). `step04_audio.py`에
      `_resolve_manual_override()`를 추가했다. 03과 마찬가지로 이 우선순위도 훅이
      아니라 `step04_audio.py` 자체 순서로 구현(이유는 위 asset_override 항목과 동일).
      ⚠ 주의: 03과 동일하게 "이미 output에 있던 파일"과 "관리자가 방금 넣은 파일"을
      소스 문구로 구분하지 못한다(둘 다 "관리자가 직접 지정한 오디오 파일"로 표기).
- [x] **03·04 둘 다 "output 캐시 먼저" 순서 버그를 다시 잡음** — 위에서 처음 구현할 때는
      03·04 모두 "output 캐시 → 관리자 지정 → 자동 생성" 순서였는데, 이러면 **이미 한
      번 처리된 장소는 관리자가 나중에 assets/에 새 파일을 넣어도 캐시에 막혀 영영
      확인되지 않는** 결함이 있었다(기능 목적 자체가 깨짐). "관리자 지정 → output
      캐시 → 자동 생성"으로 순서를 바로잡았다 — 이미 output 결과가 있는 gwandeokjeong
      으로 (1) 캐시가 있어도 새 override 파일을 넣으면 그게 우선 채택되고
      Cloudflare/SAPI 호출이 0회인 것, (2) override 없이 재실행하면 여전히 캐시를
      재사용해 불필요한 재생성이 없는 것 둘 다 실제로 확인함(03: 이미지, 04: 내레이션).
- [x] **너븐숭이 04(오디오) 채움 + Supabase 저장 + 05-assemble.py "코드-실제 불일치" 재발견·수정**
      — 너븐숭이는 04(오디오)가 아예 실행된 적이 없어서(관리자 지정 경로가 생기기
      전, 세션이 Anthropic API 크레딧 부족으로 `run_agent.py` 없이 수동으로 만든
      장소) 채워 넣었는데, 이때 `step05_assemble.py`로 05를 재조립하니 **민하님이
      관덕정·곤을동·너븐숭이에 손으로 직접 적용한 아이보리 리디자인(지도 nav·EN/KO
      토글·`archive.css` 연결·히어로 레이아웃·이중언어 렌더링)이 예전 단순 스타일로
      되돌아가는 회귀**가 재발견됐다 — 03/04 Cloudflare·SAPI 때와 완전히 같은 패턴
      (코드는 안 고치고 산출물만 손으로 고침). `step05_assemble.py`를 실제 배포된
      디자인에 맞게 다시 작성해 해결. 이 과정에서 실제 발견·수정한 버그: 비주얼 렌더링
      코드가 문헌(archival) 사진에도 무조건 `ai-generated` 클래스를 붙이고 있어서
      재생성하면 진짜 기록 사진에 "[연출]/Staged" 배지가 잘못 붙을 뻔했음(고침).
      **의도적으로 코드화하지 않은 것**: "이야기 확인 퀴즈" 섹션(스키마에 없는 손
      작성 콘텐츠, 별도 기능 필요)과 영문 문단 안의 문장 단위 "[Source: ...]" 인용
      (데이터로 없어 지어낼 수 없음) — 대신 오디오 source 문구 영문 번역은 이 프로젝트가
      직접 만든 고정 문자열이라 매핑 테이블로 추가함. 06-map의 좌표 추출도 너븐숭이
      같은 "묶음 카드"(여러 지점 표) 형식을 지원하지 못해 레지스트리(map-places.json)
      등록이 안 됐던 것을 발견해 "(본체)" 행에서 좌표를 뽑도록 수정. 전부 실제 재실행 +
      Supabase 직접 조회로 검증 완료.
- [x] **05를 "최대한 재현"까지 확장 + 관덕정·곤을동·너븐숭이 데이터 백필**
      — 01(`SourceEntry.used_for_en`/`ref_en`, 둘 다 기본값 "" — 하위호환 유지)과
      02(`quiz: List[QuizQuestion] = []`, 기본값 빈 배열 — 하위호환 유지) 스키마에
      선택 필드를 추가하고, `step05_assemble.py`에 렌더링을 실제로 구현: 이야기 확인
      퀴즈 섹션(+JS), 문단 끝에 모아 붙이는 영문 출처 인용, 출처 목록 영문 라벨,
      `.fact` span의 `title` 툴팁, 마지막 낭독 구간 `Infinity` 처리. 3개 장소 모두
      기존에 손으로 만들어져 있던 퀴즈·출처 번역 내용을 **그대로 추출해** 새 스키마
      필드에 옮겨 담았다(새로 지어낸 콘텐츠 아님). 관덕정으로 재생성 결과를 실제
      원본과 diff 떠서 공백·사소한 포맷 차이만 남고 사실상 동일함을 확인.
      **추가로 발견한 사실**: goneuldong·neobeunsungi는 `conflicts_carried_forward`
      (충돌 병기 데이터, 공통 규칙 5번)가 이미 01/02에 있는데도 05가 전혀 렌더링하지
      않고 있었음 — `_build_conflicts_html()`을 추가해 해결(단, ming의 출처별 교차
      표 대신 topic별 표로 일반화해서 렌더링 — 데이터는 같지만 레이아웃은 다름).
      **의도적으로 남겨둔 gap**: (1) 영문 문단 안 문장 단위 "[Source: ...]" 인용의
      정확한 중간 삽입 위치(문단 끝 일괄 인용으로 대체), (2) goneuldong의 인용구
      블록(`<blockquote class="verbatim">`, `verbatim_quotes` 데이터는 있지만 어느
      문장 뒤에 넣을지는 손 편집이라 자동화 안 함) — 필요하면 후속 작업으로 남음.
- [x] **01/02 Claude 프롬프트(SKILL.md·spec.md)를 실제 생성 지시로 갱신** — 위에서
      3개 장소에 손으로 백필한 en 번역·퀴즈는 스키마·렌더링만 준비된 것이었고, Claude가
      "새 카드"에서 실제로 만들어내게 하려면 프롬프트 자체를 고쳐야 했다.
      `skills/02-story/SKILL.md`·`spec.md`: "영어(en)는 구조상 자리만 남긴다(빈
      문자열)" 지시를 "en도 실제로 채운다"로 바꾸고, 퀴즈 생성(3~5개, story에 이미
      쓴 사실만 재확인·새 주장 금지)을 범위·출력 스키마·성공 기준에 추가.
      `skills/01-verify/SKILL.md`·`spec.md`: `sources[].used_for_en`/`ref_en`을
      한국어와 동일하게 실제로 채우도록 명시. ⚠ 아직 ANTHROPIC_API_KEY가 없어 이
      새 프롬프트로 실제 Claude 호출을 테스트하지는 못했다 — 키가 생기면 최우선
      확인 필요. `samples/02-story-output-example.json`(백민하 참고용 더미)은 아직
      이번 변경을 반영하지 않았음(후속 작업으로 남김).
