"""01-verify(문지기) 담당 에이전트.

카드만으로 특정 사실의 출처가 불충분하다고 판단되면 bounded_search 도구를 모델이
스스로 호출할 수 있다(미리 정해서 강제 호출하는 게 아니라 tool_choice 기본값 "auto"로
둔다 — skills/01-verify/SKILL.md ④ 참고). 카드가 충분하면 호출하지 않는다.
"""
from __future__ import annotations

from generate.common import CLAUDE_AGENTS_ROOT
from schema.step01_verify import Step01VerifyOutput
from subagents.bounded_search import bounded_search

from .base import Agent

_BOUNDED_SEARCH_TOOL = {
    "name": "bounded_search",
    "description": (
        "카드 원문만으로는 특정 사실의 출처가 불충분하다고 판단될 때, 신뢰할 수 있는 "
        "출처(공공기관·공식 사이트·언론 기사·학술 논문·지도 서비스)만으로 좁혀서 추가로 "
        "확인한다. 개인 블로그·유튜브·커뮤니티·위키 등은 이 도구가 자체적으로 배제한다. "
        "허용된 출처에서 못 찾으면 found:false만 돌아오며 절대 지어내지 않는다. "
        "카드 정보가 이미 충분하면 이 도구를 쓰지 마라."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "확인하고 싶은 사실에 대한 검색어"},
        },
        "required": ["query"],
    },
    "handler": bounded_search,
}


class VerifyAgent(Agent):
    def __init__(self):
        super().__init__(
            name="verify",
            skill_md_path=str(CLAUDE_AGENTS_ROOT / "verify-agent.md"),
            output_schema=Step01VerifyOutput,
            tools=[_BOUNDED_SEARCH_TOOL],
        )
