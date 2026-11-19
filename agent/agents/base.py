"""모든 추론형(Group A) 에이전트가 상속하는 공통 기반 클래스.

01/02/07/08이 각자 직접 하던 `llm_client.generate_validated()` 호출을 그대로
`Agent.run()`으로 옮겼다 — 순수 리팩토링이라 로직 자체는 바뀌지 않았다.

Phase C3: skill_md_path는 이제 `.claude/agents/*-agent.md`(frontmatter + SKILL.md
본문 구성)를 가리킨다. frontmatter(name/description/tools/model)는 Claude Code의
서브에이전트 자동 인식용 메타데이터일 뿐, 실제 모델에 보낼 시스템 프롬프트 본문이
아니므로 strip_frontmatter()로 제거한 뒤 사용한다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Type

from pydantic import BaseModel

from llm_client import generate_validated, generate_validated_with_tools, strip_frontmatter


class Agent:
    """name / skill_md_path(시스템 프롬프트로 쓸 .md 경로) / tools / output_schema.

    tools는 [{"name", "description", "input_schema", "handler"}] 형태의 리스트다 —
    비어 있으면(기본값) 지금까지와 동일하게 순수 generate_validated()만 쓰고, 하나라도
    있으면 Claude가 스스로 호출 여부를 판단하는 tool_use 루프를 탄다(미리 강제 호출하지
    않는다 — tool_choice는 기본값 "auto").
    """

    def __init__(self, name: str, skill_md_path: str, output_schema: Type[BaseModel], tools: list[dict] | None = None):
        self.name = name
        self.skill_md_path = skill_md_path
        self.tools: list[dict] = tools if tools is not None else []
        self.output_schema = output_schema

    def run(self, user_input: str) -> BaseModel:
        """system_prompt(=skill_md_path 파일 내용에서 frontmatter를 제거한 본문) +
        user_input으로 output_schema 인스턴스를 만든다.

        각 스텝 파일이 이전에 직접 하던
        `generate_validated(system_prompt, user_content, Model)` 호출을 그대로 옮긴 것이다
        — 재시도·검증 로직은 여전히 llm_client.generate_validated에 있다. tools가 있으면
        generate_validated_with_tools()로 위임한다.
        """
        system_prompt = strip_frontmatter(Path(self.skill_md_path).read_text(encoding="utf-8"))
        if self.tools:
            return generate_validated_with_tools(system_prompt, user_input, self.output_schema, self.tools)
        return generate_validated(system_prompt, user_input, self.output_schema)
