"""02-story 실제 생성 — Group A(추론형): 01-verify가 검증한 사실만을 재료로,
skills/02-story/SKILL.md의 지시에 따라 스토리·타임라인·챗봇 KB 초안을 만든다.
"""
from __future__ import annotations

from agents.story_agent import StoryAgent
from schema.step01_verify import Step01VerifyOutput
from schema.step02_story import Step02StoryOutput


def generate(card_text: str, step01: Step01VerifyOutput, extra_instruction: str | None = None) -> Step02StoryOutput:
    """extra_instruction: self_repair가 08 검수 fail 항목을 좁게 고쳐 달라고 덧붙이는
    추가 지시(있으면 user_content 맨 끝에 그대로 붙는다). 평소 실행에서는 None."""
    user_content = (
        "아래는 유적지 카드 원문(.md)과, 01-verify가 이미 검증한 사실·출처·인용 규칙·"
        "금지 주제·충돌·정밀도 가드레일·공개 여부다. SKILL.md의 지시에 따라 02-story 출력을 "
        "생성하라. 01의 conflicts는 conflicts_carried_forward로, precision_guardrails는 "
        "precision_guardrails_applied로, forbidden_topics와 publication_flag는 그대로 이어받아야 "
        "한다. verified_facts에 없는 사실을 새로 지어내지 마라.\n\n"
        f"## 카드 원문\n{card_text}\n\n"
        f"## 01-verify 출력\n{step01.model_dump_json(indent=2)}"
    )
    if extra_instruction:
        user_content = f"{user_content}\n\n---\n{extra_instruction}"
    return StoryAgent().run(user_content)
