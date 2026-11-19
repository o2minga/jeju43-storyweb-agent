---
name: 04-audio
description: 02-story의 원고(story)를 입력으로 받아, 차분하고 객관적인 톤의 TTS 오디오 가이드(ko)와 로열티 프리/자체 생성 BGM, 스크립트 싱크 타임라인, 웹 오디오 에셋 패키지를 만든다. 스토리 페이지에 낭독 오디오와 배경음이 필요할 때 사용한다. 무단 상업용 BGM은 쓰지 않는다.
---

# 04-audio ‹음향감독›

## ① 목표
02 원고를 왜곡 없이 정확한 발음으로 읽어주는 **차분한 TTS 오디오 가이드**와, 장소성에 맞는 **절제된 BGM**을 만든다. 자극적·과장된 연출을 피하고, 05-assemble의 오디오 플레이어 블록에 바로 연동되는 에셋을 낸다.

## ② 맥락
- 입력:
  - `samples/02-story-output-example.json`의 `story.{intro,development,closing}.{ko,en}` — 낭독 원고
  - (있으면) `timeline_events` — 싱크 타임라인 참고
  - `location_name` — 파일 경로·식별용
- 출력: 05-assemble이 **오디오 플레이어 블록**으로 물려 쓴다. → `samples/04-audio-output-example.json` 형식으로 wav 경로·싱크·메타데이터를 넘긴다.
- 아키텍처: `AGENT-SPEC.md` 5장 기준 **B그룹(미디어 생성형)**. 03(비주얼)과 동일하게 **관리자 지정 오디오가 항상 최우선이다 — output 캐시보다도 먼저 확인한다**: 프로젝트 루트 `assets/{location_id}/{narration-ko.wav|bgm.wav}`에 관리자가 직접 만들어 넣은 파일이 있으면 그대로 채택한다(output 캐시를 먼저 보면 이미 처리된 장소에 관리자가 나중에 새 파일을 넣어도 확인되지 않으므로 순서가 중요하다). 없을 때만 `output/{location_id}/audio/` 캐시를 재사용하고, 그것도 없을 때만 실제 합성을 시도한다 — 내레이션은 Windows SAPI(오프라인 TTS, 기본 음성 "Microsoft Heami Desktop")로, BGM은 절차적 합성(numpy)으로 만든다(`agent/generate/audio_backend.py`) — 둘 다 클라우드 API 키가 필요 없다. Windows가 아니거나 해당 음성이 없어 합성이 실패하면 조용히 placeholder로 폴백한다.
- (구현 메모) 이 우선순위도 파이프라인 훅(`agent/hooks/`)이 아니라 `step04_audio.py` 자체의 순서로 구현했다 — 03과 같은 이유(훅 시스템이 실행 흐름에 개입할 통로가 없음, `PROGRESS.md`의 "파이프라인 훅" 절 참고).
- 언어: **ko만 채우고 en은 자리만** 남긴다(02의 영어 대본 완성 후 대응).

## ③ 범위 (포함 / 제외)
**포함**
- 02 원고 → 자연스러운 TTS 음성(ko) 생성
- 고유명사·역사 용어 발음 사전 적용
- 장소성에 맞는 차분한 BGM 매칭(로열티 프리 또는 자체 AI 생성)
- BGM ↔ 음성 음량 밸런싱
- 스크립트 싱크 타임라인 데이터(문단·문장 단위 시작 시각)
- 05 오디오 플레이어에 즉시 연동되는 에셋 패키지 출력

**제외**
- 원고 텍스트 편집·번역 (02 영역)
- 이미지·영상 (03 영역), 웹 조립 (05 영역), 챗봇 (07 영역)
- 클라우드 TTS 음색·속도의 세부 튜닝 (지금은 Windows SAPI 기본 음성 그대로 사용)

## ④ 제약 (반드시 지킴)

### 1) 차분·객관 톤
- 자극적·과장된 낭독, 감정 과잉 연출 금지. 다큐멘터리 내레이션 같은 절제된 톤.

### 2) 발음 정확성 (발음 사전)
- 고유명사·역사 용어는 **발음 사전**을 적용해 왜곡 없이 읽는다.
- 발음 사전은 카드/원고에서 등장하는 용어를 대상으로 구성한다(특정 카드에 하드코딩하지 않고, 원고에서 추출해 채운다).

### 3) BGM 저작권
- **무단 상업용 BGM 금지.** 로열티 프리 또는 자체 AI 생성 음악 에셋만 사용한다.
- AI 음성·음악 생성 시 출처(생성 도구/라이선스)를 메타데이터에 표기한다.

### 4) 밸런싱
- BGM이 낭독을 가리지 않게 음량을 낮춘다(음성 우선).

### 5) 언어 라벨
- `ko`만 실제 생성하고 `en`은 구조상 자리만 둔다. 02 영어 대본이 완성되면 대응.

## ⑤ 출력 형식
`samples/04-audio-output-example.json` 형식으로 산출한다.

```json
{
  "location_id": "{장소_식별자}",
  "narration": {
    "lang": "ko",
    "path": "output/{location_id}/audio/narration-ko.wav",
    "source": "AI TTS (Microsoft Heami Desktop, ko-KR, Windows SAPI 오프라인 합성)", // 관리자가 assets/{location_id}/narration-ko.wav를 직접 넣어뒀으면 "AI TTS (관리자가 직접 지정한 오디오 파일)"
    "is_ai_generated": true,
    "tone": "차분·객관",
    "en": null
  },
  "bgm": {
    "path": "output/{location_id}/audio/bgm.wav",
    "license": "royalty-free | self-generated",
    "source": "자체 생성 앰비언트 패드 (numpy 합성, 로열티 프리)", // 관리자 지정 파일이면 "자체 생성 BGM (관리자가 직접 지정한 오디오 파일)"
    "volume_relative_to_narration": 0.25
  },
  "pronunciation_dict": [
    {"term": "{고유명사/용어}", "reading": "{발음 표기}"}
  ],
  "sync_timeline": [
    {"segment_id": "intro", "start_sec": 0.0, "end_sec": 0.0, "text_ref": "story.intro.ko"}
  ],
  "web_asset_package": {
    "player_block": "audio",
    "files": ["output/{location_id}/audio/narration-ko.wav", "output/{location_id}/audio/bgm.wav"],
    "notes": "05-assemble 오디오 플레이어 블록에 즉시 연동"
  }
}
```

- `story`가 비면 narration을 만들지 않고 해당 필드를 빈 값/`null`로 둔다(지어내지 않음).
- TTS 음성·BGM은 AI/생성 에셋이므로 출처 대장(08)에는 포함되지 않는다 — 웹 내 표기로만 관리.

## ⑥ 성공 기준
- 원고가 왜곡 없이, 발음 사전이 적용된 정확한 발음으로 읽힌다
- 낭독 톤이 차분·객관적이다(과장 없음)
- BGM이 로열티 프리/자체 생성이고 출처가 표기된다
- BGM/음성 음량 밸런스가 양호하다(음성 우선)
- 싱크 타임라인이 문단 단위로 제공된다
- 출력 JSON이 05 오디오 플레이어에 즉시 연동된다

---

## 공통 규칙 (감점 방지선 — 8개 스킬 공통)
1. **출처 표기 필수** — AI 음성·음악의 생성 도구/라이선스 표기. 개인 블로그·유튜브 금지.
2. **쉬운 언어** — 낭독 원고(02)는 이미 쉬운 언어. 04는 그 톤을 유지한다.
3. **사실 vs 연출 구분** — AI 생성 음성·음악은 생성 에셋으로 표기(문헌 자료 아님).
4. **지어내기 금지** — 원고에 없는 문장을 낭독으로 추가하지 않는다.
5. **충돌 시 병기** — 원고가 병기한 사실은 낭독도 그대로 병기해 읽는다(임의 확정 금지).

## 입력 예시 / 출력 예시
- 입력: `samples/02-story-output-example.json` → `story`, `timeline_events`
- 출력: `samples/04-audio-output-example.json` (본 스킬 산출물 계약 — 박이현(05)에게 공유)
