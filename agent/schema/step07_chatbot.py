"""07-chatbot 출력 스키마 — skills/07-chatbot/spec.md 6장(출력 형식)을 그대로 반영."""
from __future__ import annotations

from typing import List

from .common import LangText, StrictModel


class KBEntry(StrictModel):
    qa_id: str
    question: LangText
    answer: LangText
    source: str
    tags: List[str]


class Guardrail(StrictModel):
    system_prompt: str
    fallback_answer: LangText
    refuse_topics: List[str]
    conflict_note: str


class Widget(StrictModel):
    launcher: str
    modal_script_path: str
    notes: str


class Step07ChatbotOutput(StrictModel):
    location_id: str
    kb: List[KBEntry]
    guardrail: Guardrail
    widget: Widget
