"""04-audio 실제 생성 — Group B(미디어 생성형).

이미지(03)와 동일한 우선순위를 따른다 — **관리자 지정 오디오가 항상 최우선이다
(output 캐시보다도 먼저 본다)**. 캐시를 먼저 보면, 이미 한 번 처리된 장소에 관리자가
나중에 새 파일을 넣어도 캐시에 막혀 영영 확인되지 않아 "나중에 바꿔 넣기"라는 기능
목적이 깨지기 때문이다:
1. 프로젝트 루트 assets/{location_id}/{narration-ko.wav|bgm.wav}(관리자가 직접 만들어
   넣는 자리)에 파일이 있으면 그것을 output/ 쪽으로 복사해 채택하고, 자동 합성은
   호출하지 않는다.
2. 없으면 output/{location_id}/audio/{narration-ko.wav|bgm.wav} 캐시를 본다 — 있으면
   그대로 재사용한다(재생성 비용 절약용).
3. 그래도 없을 때만 실제 합성을 시도한다 — 내레이션은 Windows SAPI(오프라인 TTS,
   기본 음성 "Microsoft Heami Desktop"), BGM은 절차적으로 합성한 로열티 프리
   앰비언트 패드(audio_backend.py). Windows가 아니거나 해당 음성이 없어 합성이
   실패하면 조용히 placeholder로 폴백해 파이프라인을 막지 않는다.

- 발음 사전은 실제 한국어 경음화(된소리) 지식이 필요한 단어(예: 지명·고유명사)는 규칙만으로
  안전하게 추측할 수 없어 만들어내지 않는다 — 대신 연도처럼 순수 산술로 정확히 읽을 수 있는
  숫자(한자어 수 읽기)만 자동 추출한다. 지어내지 않는다는 프로젝트 원칙과 일관된 선택이다.
- 낭독 구간(sync_timeline)은 실제 합성된 wav 길이를 문단 글자 수 비례로 나눈 값이다.
  placeholder로 폴백한 경우에만 글자 수 비례 추정치(_CHARS_PER_SEC)를 대신 쓴다.
"""
from __future__ import annotations

import logging
import re
from typing import List

from generate import audio_backend
from generate.common import OUTPUT_ROOT, location_asset_path
from schema.step02_story import Step02StoryOutput
from schema.step04_audio import Bgm, Narration, PronunciationEntry, Step04AudioOutput, SyncTimelineEntry, WebAssetPackage

logger = logging.getLogger("agent.generate.step04_audio")

ASSETS_ROOT = OUTPUT_ROOT.parent / "assets"  # 관리자가 직접 만든 파일을 넣는 레거시 자리(03과 동일)

_DIGIT_NAMES = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
_YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
_CHARS_PER_SEC = 6.0  # 실제 낭독 파일이 없을 때만 쓰는 낭독 속도 추정치(placeholder 폴백)

_PLACEHOLDER_NARRATION_SOURCE = "AI TTS (placeholder)"
_REAL_NARRATION_SOURCE = "AI TTS (Microsoft Heami Desktop, ko-KR, Windows SAPI 오프라인 합성)"
_MANUAL_NARRATION_SOURCE = "AI TTS (관리자가 직접 지정한 오디오 파일)"
_PLACEHOLDER_BGM_SOURCE = "자체 AI 생성 BGM (placeholder)"
_REAL_BGM_SOURCE = "자체 생성 앰비언트 패드 (numpy 합성, 로열티 프리)"
_MANUAL_BGM_SOURCE = "자체 생성 BGM (관리자가 직접 지정한 오디오 파일)"

_DEFAULT_BGM_DURATION_SEC = 60.0


def _sino_year_reading(year: int) -> str:
    thousands, rem = divmod(year, 1000)
    hundreds, rem = divmod(rem, 100)
    tens, ones = divmod(rem, 10)
    parts = []
    if thousands:
        parts.append(("" if thousands == 1 else _DIGIT_NAMES[thousands]) + "천")
    if hundreds:
        parts.append(("" if hundreds == 1 else _DIGIT_NAMES[hundreds]) + "백")
    if tens:
        parts.append(("" if tens == 1 else _DIGIT_NAMES[tens]) + "십")
    if ones:
        parts.append(_DIGIT_NAMES[ones])
    return "".join(parts) or "영"


def _extract_pronunciation_dict(step02: Step02StoryOutput) -> List[PronunciationEntry]:
    text = " ".join(
        [step02.story.intro.ko, step02.story.development.ko, step02.story.closing.ko]
        + [f"{e.title.ko} {e.description.ko}" for e in step02.timeline_events]
    )
    years = sorted({int(y) for y in _YEAR_RE.findall(text)})
    return [PronunciationEntry(term=str(y), reading=_sino_year_reading(y)) for y in years]


def _is_story_empty(step02: Step02StoryOutput) -> bool:
    s = step02.story
    return not (s.intro.ko.strip() or s.development.ko.strip() or s.closing.ko.strip())


def _resolve_manual_override(location_id: str, filename: str) -> str | None:
    """관리자 지정 파일(assets/{location_id}/{filename})을 output 캐시보다 먼저 본다 —
    캐시를 먼저 보면, 이미 한 번 처리된 장소에 관리자가 나중에 새 파일을 넣어도 캐시에
    막혀 영영 확인되지 않아 "나중에 바꿔 넣기"라는 기능 목적이 깨지기 때문이다.

    있으면 output/ 쪽으로 복사하고 "manual-legacy-copy"를 반환한다. 없으면
    output/{location_id}/audio/{filename} 캐시를 본다 — 있으면 "existing-output"
    (재생성 비용 절약). 둘 다 없으면 None — 호출부가 자동 합성을 시도해야 한다는 뜻이다.
    """
    target_abs = OUTPUT_ROOT / location_id / "audio" / filename

    legacy_path = ASSETS_ROOT / location_id / filename
    if legacy_path.exists():
        logger.info(
            "관리자 지정 오디오 우선 확인: %s에 파일이 있어 자동 합성 없이 그대로 사용합니다.",
            legacy_path,
        )
        target_abs.parent.mkdir(parents=True, exist_ok=True)
        target_abs.write_bytes(legacy_path.read_bytes())
        return "manual-legacy-copy"

    if target_abs.exists():
        return "existing-output"

    return None


def _build_bgm(location_id: str, duration_sec: float) -> Bgm:
    path = location_asset_path(location_id, "audio", "bgm.wav")
    abs_path = OUTPUT_ROOT / location_id / "audio" / "bgm.wav"

    origin = _resolve_manual_override(location_id, "bgm.wav")
    if origin is None:
        try:
            audio_backend.synthesize_bgm(abs_path, duration_sec=max(duration_sec, 30.0))
            origin = "synthesized"
        except Exception:  # noqa: BLE001 - 합성 실패는 placeholder 폴백 신호일 뿐, 파이프라인을 죽이지 않는다
            return Bgm(
                path=path,
                license="self-generated",
                source=_PLACEHOLDER_BGM_SOURCE,
                volume_relative_to_narration=0.25,
            )

    source = _REAL_BGM_SOURCE if origin == "synthesized" else _MANUAL_BGM_SOURCE
    return Bgm(path=path, license="self-generated", source=source, volume_relative_to_narration=0.25)


def generate(location_id: str, step02: Step02StoryOutput) -> Step04AudioOutput:
    if _is_story_empty(step02):
        bgm = _build_bgm(location_id, duration_sec=_DEFAULT_BGM_DURATION_SEC)
        return Step04AudioOutput(
            location_id=location_id,
            narration=None,
            bgm=bgm,
            pronunciation_dict=[],
            sync_timeline=[],
            web_asset_package=WebAssetPackage(
                player_block="audio",
                files=[bgm.path],
                notes="story가 비어 있어 낭독은 생성하지 않음 (spec.md 6장) — BGM만 연동",
            ),
        )

    narration_path = location_asset_path(location_id, "audio", "narration-ko.wav")
    narration_abs = OUTPUT_ROOT / location_id / "audio" / "narration-ko.wav"

    full_text = "\n".join([step02.story.intro.ko, step02.story.development.ko, step02.story.closing.ko])
    narration_origin = _resolve_manual_override(location_id, "narration-ko.wav")
    if narration_origin is None:
        if audio_backend.synthesize_narration(full_text, narration_abs):
            narration_origin = "synthesized"
    tts_ready = narration_abs.exists()

    if narration_origin == "synthesized":
        narration_source = _REAL_NARRATION_SOURCE
    elif narration_origin in ("existing-output", "manual-legacy-copy"):
        narration_source = _MANUAL_NARRATION_SOURCE
    else:
        narration_source = _PLACEHOLDER_NARRATION_SOURCE

    narration = Narration(
        lang="ko",
        path=narration_path,
        source=narration_source,
        is_ai_generated=True,
        tone="차분·객관",
        en=None,
    )

    segments = [
        ("intro", step02.story.intro.ko),
        ("development", step02.story.development.ko),
        ("closing", step02.story.closing.ko),
    ]
    char_counts = [len(text) for _, text in segments]
    total_chars = sum(char_counts) or 1
    total_duration = audio_backend.wav_duration_sec(narration_abs) if tts_ready else total_chars / _CHARS_PER_SEC

    sync_timeline = []
    cursor = 0.0
    for (segment_id, _text), chars in zip(segments, char_counts):
        duration = max(total_duration * (chars / total_chars), 0.1)
        sync_timeline.append(
            SyncTimelineEntry(
                segment_id=segment_id,
                start_sec=round(cursor, 1),
                end_sec=round(cursor + duration, 1),
                text_ref=f"story.{segment_id}.ko",
            )
        )
        cursor += duration

    bgm = _build_bgm(location_id, duration_sec=total_duration)

    return Step04AudioOutput(
        location_id=location_id,
        narration=narration,
        bgm=bgm,
        pronunciation_dict=_extract_pronunciation_dict(step02),
        sync_timeline=sync_timeline,
        web_asset_package=WebAssetPackage(
            player_block="audio",
            files=[narration.path, bgm.path],
            notes="05-assemble 오디오 플레이어 블록에 즉시 연동",
        ),
    )
