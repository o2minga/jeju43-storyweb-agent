"""05-assemble 출력 검증 — skills/05-assemble/spec.md 5장(마크업 규칙)·6장(제약) 반영.

05의 산출물은 JSON이 아니라 .html이므로, 순수 Pydantic 모델로 "출력 스키마"를 표현할
대상이 없다. 대신 spec.md 5장이 정의한 마크업 규칙(class="fact", data-fact-id,
class="ai-generated", 챗봇 모달 컨테이너, 출처 footer 등)을 BeautifulSoup으로 뽑아
구조화한 뒤, 그 결과를 Pydantic 모델로 검증한다. 08-review의 점검 방법(spec.md 4장)과
같은 추출 로직을 재사용할 수 있게 설계했다.
"""
from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup
from pydantic import model_validator

from .common import StrictModel


class FactSpan(StrictModel):
    fact_id: str
    source: str


class AiGeneratedFigure(StrictModel):
    origin: str
    has_effect_caption: bool


class ArchiveFigure(StrictModel):
    origin: str


class TimelineEventRef(StrictModel):
    event_id: str


class SourceFooterEntry(StrictModel):
    source_ref: str


class Step05AssembleOutput(StrictModel):
    internal_only_meta_present: bool
    fact_spans: List[FactSpan]
    ai_generated_figures: List[AiGeneratedFigure]
    archive_figures: List[ArchiveFigure]
    timeline_events: List[TimelineEventRef]
    chatbot_modal_present: bool
    sources_footer: List[SourceFooterEntry]
    # 02의 sources_by_sentence 중 문단 안에서 부분 문자열로 못 찾은 문장의 sentence_id 목록.
    # agent/generate/step05_assemble.py가 조립 시 hidden 마커(#unmatched-fact-sentences)로
    # 남겨 두면 여기서 읽어 온다 — 조용히 누락시키지 않고 검증 단계에서 fail로 잡기 위함.
    unmatched_sentence_ids: List[str] = []

    @model_validator(mode="after")
    def _check_rules(self):
        for span in self.fact_spans:
            if not span.fact_id:
                raise ValueError("class=\"fact\" 요소에 data-fact-id가 없습니다.")
            if not span.source:
                raise ValueError(
                    f"data-fact-id={span.fact_id!r} 요소에 data-source가 없습니다 "
                    "(출처 없는 사실 문장은 조립하지 않아야 함)."
                )
        for fig in self.ai_generated_figures:
            if not fig.has_effect_caption:
                raise ValueError(
                    "class=\"ai-generated\" figure의 figcaption에 '[연출]' 표시가 없습니다."
                )
        if self.unmatched_sentence_ids:
            raise ValueError(
                "02-story.json의 sources_by_sentence 중 문단에서 부분 문자열로 찾지 못한 "
                f"문장이 있습니다: {', '.join(self.unmatched_sentence_ids)}"
            )
        return self


def parse_assemble_html(html: str) -> Step05AssembleOutput:
    soup = BeautifulSoup(html, "html.parser")

    fact_spans = [
        FactSpan(fact_id=el.get("data-fact-id", ""), source=el.get("data-source", ""))
        for el in soup.select(".fact")
    ]

    ai_figures = []
    for fig in soup.select("figure.ai-generated"):
        caption = fig.find("figcaption")
        caption_text = caption.get_text() if caption else ""
        ai_figures.append(
            AiGeneratedFigure(
                origin=fig.get("data-origin", ""),
                has_effect_caption="[연출]" in caption_text,
            )
        )

    archive_figures = [
        ArchiveFigure(origin=fig.get("data-origin", ""))
        for fig in soup.select('figure[data-origin="archive"]')
        if "ai-generated" not in (fig.get("class") or [])
    ]

    timeline_events = [
        TimelineEventRef(event_id=el.get("data-event-id", ""))
        for el in soup.select(".timeline-event")
    ]

    modal = soup.select_one("#chatbot-modal[data-kb-source]")

    sources_footer = [
        SourceFooterEntry(source_ref=el.get("data-source-ref", ""))
        for el in soup.select("footer.sources li[data-source-ref]")
    ]

    meta = soup.select_one('meta[name="internal-only"]')
    internal_only_present = bool(meta and meta.get("content") == "true")

    unmatched_marker = soup.select_one("#unmatched-fact-sentences")
    unmatched_sentence_ids = []
    if unmatched_marker and unmatched_marker.get("data-sentence-ids"):
        unmatched_sentence_ids = [s for s in unmatched_marker["data-sentence-ids"].split(",") if s]

    return Step05AssembleOutput(
        internal_only_meta_present=internal_only_present,
        fact_spans=fact_spans,
        ai_generated_figures=ai_figures,
        archive_figures=archive_figures,
        timeline_events=timeline_events,
        chatbot_modal_present=modal is not None,
        sources_footer=sources_footer,
        unmatched_sentence_ids=unmatched_sentence_ids,
    )
