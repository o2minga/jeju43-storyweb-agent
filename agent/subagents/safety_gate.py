"""safety_gate — 03-visual이 이미지를 실제로 생성하기 전에 항상 먼저 거치는
재현 금지 게이트 (skills/03-visual/spec.md 4장).

차단 대상(spec.md 4-1):
- 잔인한 피해 장면의 직접 묘사(시신·부상·피 등)
- 실존 인물(피해자·생존자·가해자)의 식별 가능한 얼굴 재현
- 폭력 행위(총살·처형·구타·연행·발포 등)가 실행되는 순간의 사실적 재현

차단되면 지어낸 장면이 아니라, spec.md 4-3의 우회 변환 대응표 취지(사건이 벌어진
장소의 현재 모습·남겨진 사물·빈 공간 등 "지금 실제로 있을 법한 상징")에 맞는 대체
표현을 제안한다 — 새로운 사실을 지어내는 게 아니라 장면을 안전하게 우회하는 것만
담당한다.
"""
from __future__ import annotations

import logging

from pydantic import model_validator

from generate.common import CLAUDE_AGENTS_ROOT
from llm_client import generate_validated, strip_frontmatter
from schema.common import StrictModel

logger = logging.getLogger("agent.subagents.safety_gate")

_SYSTEM_PROMPT_PATH = CLAUDE_AGENTS_ROOT / "visual-safety-agent.md"


def _load_system_prompt() -> str:
    """`.claude/agents/visual-safety-agent.md`(frontmatter 포함)에서 frontmatter를
    걷어낸 본문을 읽는다 — Phase C3: safety_gate 전용 서브에이전트 정의로 이전."""
    return strip_frontmatter(_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"))


class SafetyGateVerdict(StrictModel):
    passed: bool
    reason: str
    suggested_alternative: str = ""

    @model_validator(mode="after")
    def _check_alternative_present_when_blocked(self):
        if not self.passed and not self.suggested_alternative.strip():
            raise ValueError("차단(passed=false)이면 suggested_alternative(상징적 대체 표현)가 반드시 있어야 합니다.")
        return self


def safety_gate(image_prompt: str) -> dict:
    """image_prompt 하나를 검사해 {"passed", "reason", "suggested_alternative"}를 반환한다.

    suggested_alternative는 차단(passed:false)일 때만 값이 있고, 통과(passed:true)면
    None이다. 이 함수 자체는 이미지를 생성하지 않는다 — 텍스트 판단 하나뿐이라 실제
    이미지 생성 API 키 없이도 지금 바로 실제 Claude 호출로 테스트할 수 있다.
    """
    logger.info("safety_gate 호출: image_prompt=%r", image_prompt)
    verdict = generate_validated(_load_system_prompt(), image_prompt, SafetyGateVerdict)

    result = {
        "passed": verdict.passed,
        "reason": verdict.reason,
        "suggested_alternative": verdict.suggested_alternative if not verdict.passed else None,
    }
    logger.info("safety_gate 결과: passed=%s reason=%s", result["passed"], result["reason"])
    return result
