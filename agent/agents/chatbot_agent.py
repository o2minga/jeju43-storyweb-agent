"""07-chatbot(안내원) 담당 에이전트."""
from __future__ import annotations

from generate.common import CLAUDE_AGENTS_ROOT
from schema.step07_chatbot import Step07ChatbotOutput

from .base import Agent


class ChatbotAgent(Agent):
    def __init__(self):
        super().__init__(
            name="chatbot",
            skill_md_path=str(CLAUDE_AGENTS_ROOT / "chatbot-agent.md"),
            output_schema=Step07ChatbotOutput,
        )
