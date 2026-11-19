"""01-verify 실제 생성 — Group A(추론형): skills/01-verify/SKILL.md를 시스템 프롬프트로,
카드 원문을 사용자 메시지로 보내 Step01VerifyOutput을 생성한다.
"""
from __future__ import annotations

from agents.verify_agent import VerifyAgent
from schema.step01_verify import Step01VerifyOutput


def generate(card_text: str, extra_instruction: str | None = None) -> Step01VerifyOutput:
    """extra_instruction: self_repair가 08 검수 fail 항목을 좁게 고쳐 달라고 덧붙이는
    추가 지시(있으면 user_content 맨 끝에 그대로 붙는다). 평소 실행(run_agent.py가
    --repair 없이 호출)에서는 None이라 기존 프롬프트와 완전히 동일하다."""
    user_content = (
        "아래는 유적지 카드 원문(.md)이다. SKILL.md의 지시에 따라 01-verify 출력을 생성하라.\n"
        "카드에 없는 내용은 만들어내지 말고, 카드 안의 출처 표기(대괄호·표·원문 인용·⚠주의)를 "
        "빠짐없이 반영하라.\n\n"
        f"## 카드 원문\n{card_text}"
    )
    if extra_instruction:
        user_content = f"{user_content}\n\n---\n{extra_instruction}"
    return VerifyAgent().run(user_content)
