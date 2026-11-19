"""01-verify 출력 스키마 — skills/01-verify/spec.md 6장(출력 형식)을 그대로 반영.

conflicts / precision_guardrails는 spec.md 4장 3번 규칙("항상 둘 다 스키마에 존재해야
하며, 해당하는 내용이 없으면 빈 배열로 둔다")에 따라 기본값을 주지 않는다 — 그래야
페이로드에 키 자체가 빠졌을 때 Pydantic이 "필드 누락"으로 명확히 걸러낸다. 값은
빈 리스트([])여도 되지만, 키가 아예 없으면 에러가 나야 한다.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from .common import StrictModel


class FactSource(StrictModel):
    type: Literal["card", "search"]
    ref: str


class VerifiedFact(StrictModel):
    fact_id: str
    text: str
    source: FactSource
    note: Optional[str] = None


class SourceEntry(StrictModel):
    ref: str
    used_for: str
    # 영문 번역 — 기본값 ""(선택적)이라 예전에 만든 01-verify.json(이 필드가 아예 없던
    # 시절 산출물)도 그대로 유효하다. 비어 있으면 05-assemble이 영문 출처 목록에서
    # 이 항목을 그냥 생략한다(없는 번역을 지어내지 않음).
    used_for_en: str = ""
    # 이 출처(ref) 자체의 영문 표기 — 영문 문단 안에 붙는 "[Source: ...]" 인용에 쓴다.
    # 기본값 ""(선택적)이고, 비어 있으면 05-assemble이 그 문단에는 영문 인용을 붙이지
    # 않는다(한국어 ref 이름을 영문 문장에 그대로 노출하지 않기 위함).
    ref_en: str = ""


class CitationGuideEntry(StrictModel):
    format: str
    when: str


class VerbatimQuote(StrictModel):
    id: str
    text: str
    source: str
    modification_allowed: bool


class ConflictValue(StrictModel):
    value: str
    source: str


class Conflict(StrictModel):
    topic: str
    values: List[ConflictValue]
    resolution: str


class PrecisionGuardrail(StrictModel):
    topic: str
    rule: str


class PublicationFlag(StrictModel):
    internal_only: bool
    note: str


class Step01VerifyOutput(StrictModel):
    location_id: str
    verified_facts: List[VerifiedFact]
    sources: List[SourceEntry]
    citation_guide: List[CitationGuideEntry]
    verbatim_quotes: List[VerbatimQuote]
    forbidden_topics: List[str]
    conflicts: List[Conflict]  # 빈 배열 허용, 키 누락은 불허 (기본값 없음)
    precision_guardrails: List[PrecisionGuardrail]  # 위와 동일
    publication_flag: PublicationFlag
