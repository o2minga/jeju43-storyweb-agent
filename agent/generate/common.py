"""agent/generate/의 각 스텝 생성기 모듈이 공유하는 경로·입출력 헬퍼."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
OUTPUT_ROOT = REPO_ROOT / "output"
CLAUDE_AGENTS_ROOT = REPO_ROOT / ".claude" / "agents"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def location_asset_path(location_id: str, *parts: str) -> str:
    """output/{location_id}/... 형태의, 05-assemble.html 등에 저장할 경로 문자열."""
    return "/".join(["output", location_id, *parts])
