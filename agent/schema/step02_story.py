"""02-story 출력 스키마 — skills/02-story/spec.md 6장(출력 형식)을 그대로 반영."""
from __future__ import annotations

from typing import List, Literal, Optional

from .common import LangText, StrictModel


class Story(StrictModel):
    intro: LangText
    development: LangText
    closing: LangText


class SourceBySentence(StrictModel):
    sentence_id: str
    text_snippet: LangText
    source: str
    source_type: Literal["card", "search"]


class ConflictValue(StrictModel):
    value: str
    source: str


class ConflictCarriedForward(StrictModel):
    topic: str
    values: List[ConflictValue]
    how_handled: str


class PrecisionGuardrailApplied(StrictModel):
    topic: str
    how_handled: str


class ImagePromptDraft(StrictModel):
    prompt_id: str
    scene: LangText
    mood: str
    note_for_03: str


class TimelineEvent(StrictModel):
    event_id: str
    date: str  # "YYYY-MM-DD" | "YYYY" | "시기 불명" 등 — spec.md가 자유 형식을 허용
    title: LangText
    description: LangText
    source: str


class ChatbotKBEntry(StrictModel):
    qa_id: str
    question: LangText
    answer: LangText
    source: str
    note_for_07: Optional[str] = None


class QuizChoice(StrictModel):
    choice_id: str  # "a" | "b" | "c" 등, quiz_question.correct_choice_id가 이 중 하나를 가리킴
    text: LangText


class QuizQuestion(StrictModel):
    """이야기 확인 퀴즈 문항 — story에 이미 있는 사실만 재확인하는 용도라, 카드/검증된
    사실 밖의 새 주장을 만들지 않는다(지어내기 금지 원칙과 동일하게 적용)."""

    question_id: str
    question: LangText
    choices: List[QuizChoice]
    correct_choice_id: str
    explanation: LangText


class TargetMode(StrictModel):
    current: Literal["중고생", "성인", "외국인"]
    options: List[str]
    note: str


class PublicationFlag(StrictModel):
    internal_only: bool
    note: str


class Step02StoryOutput(StrictModel):
    location_id: str
    location_name: LangText
    story: Story
    sources_by_sentence: List[SourceBySentence]
    forbidden_topics: List[str]
    conflicts_carried_forward: List[ConflictCarriedForward]
    precision_guardrails_applied: List[PrecisionGuardrailApplied]
    image_prompts_draft: List[ImagePromptDraft]
    timeline_events: List[TimelineEvent]
    chatbot_kb: List[ChatbotKBEntry]
    quiz: List[QuizQuestion] = []  # 기본값 빈 배열 — 예전 02-story.json(이 필드가 없던 산출물)도 그대로 유효
    target_mode: TargetMode
    publication_flag: PublicationFlag
