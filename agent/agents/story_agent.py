"""02-story(번역가) 담당 에이전트."""
from __future__ import annotations

from generate.common import CLAUDE_AGENTS_ROOT
from schema.step02_story import Step02StoryOutput

from .base import Agent


class StoryAgent(Agent):
    def __init__(self):
        super().__init__(
            name="story",
            skill_md_path=str(CLAUDE_AGENTS_ROOT / "story-agent.md"),
            output_schema=Step02StoryOutput,
        )
