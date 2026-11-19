"""04-audio 출력 스키마 — skills/04-audio/spec.md 6장(출력 형식)을 그대로 반영.

story가 비어 있으면 narration을 만들지 않고 null로 둔다는 규칙(spec.md 2장·6장)에 따라,
narration 필드는 "키는 항상 있어야 하지만 값은 null일 수 있다"로 모델링한다
(기본값을 주지 않아 키 누락은 여전히 에러가 나게 한다).
"""
from __future__ import annotations

from typing import List, Literal, Optional

from .common import StrictModel


class Narration(StrictModel):
    lang: Literal["ko"]
    path: str
    source: str
    is_ai_generated: bool
    tone: str
    en: Optional[str]  # 구조상 자리만 — 값은 null 허용, 키는 항상 존재


class Bgm(StrictModel):
    path: str
    license: Literal["royalty-free", "self-generated"]
    source: str
    volume_relative_to_narration: float


class PronunciationEntry(StrictModel):
    term: str
    reading: str


class SyncTimelineEntry(StrictModel):
    segment_id: str
    start_sec: float
    end_sec: float
    text_ref: str


class WebAssetPackage(StrictModel):
    player_block: str
    files: List[str]
    notes: str


class Step04AudioOutput(StrictModel):
    location_id: str
    narration: Optional[Narration]  # story가 비면 null (키는 항상 존재)
    bgm: Bgm
    pronunciation_dict: List[PronunciationEntry]
    sync_timeline: List[SyncTimelineEntry]
    web_asset_package: WebAssetPackage
