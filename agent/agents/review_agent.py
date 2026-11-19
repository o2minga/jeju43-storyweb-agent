"""08-review(감수관) 담당 에이전트.

08의 6개 점검 중 실제로 Claude 판단이 필요한 건 ③지어내기 여부 하나뿐이다(나머지
①②④⑤⑥은 agent/generate/step08_review.py가 코드로 직접 판정한다). 그래서 이 에이전트의
system_prompt는 08-review SKILL.md 전체가 아니라, ③ 판정만 스코프를 좁힌
`.claude/agents/review-agent.md`(구 skills/08-review/fabrication-system-prompt.md와
동일 내용)이고, output_schema도 최종 산출물인 Step08ReviewOutput이 아니라 그 안의
checks[] 항목 하나인 CheckResult다.
"""
from __future__ import annotations

from generate.common import CLAUDE_AGENTS_ROOT
from schema.step08_review import CheckResult

from .base import Agent


class ReviewAgent(Agent):
    def __init__(self):
        super().__init__(
            name="review",
            skill_md_path=str(CLAUDE_AGENTS_ROOT / "review-agent.md"),
            output_schema=CheckResult,
        )
