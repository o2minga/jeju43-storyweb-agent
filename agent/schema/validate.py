"""스텝 번호만 알면 알맞은 스키마로 검증해주는 단일 진입점.

run_agent.py는 이 모듈의 validate_step()만 호출하면 되고, 01~04·07·08(JSON)과
05·06(HTML) 사이의 차이를 신경 쓸 필요가 없다.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from pydantic import ValidationError

from .common import SchemaValidationError, format_validation_error
from .step01_verify import Step01VerifyOutput
from .step02_story import Step02StoryOutput
from .step03_visual import Step03VisualOutput
from .step04_audio import Step04AudioOutput
from .step05_assemble import parse_assemble_html
from .step06_map import parse_map_html
from .step07_chatbot import Step07ChatbotOutput
from .step08_review import Step08ReviewOutput

# step_id -> (output/{location_id}/ 아래 파일명 또는 None(=06처럼 위치 폴더 밖), 파일 종류)
STEP_FILES: Dict[str, Tuple[str | None, str]] = {
    "01": ("01-verify.json", "json"),
    "02": ("02-story.json", "json"),
    "03": ("03-visual.json", "json"),
    "04": ("04-audio.json", "json"),
    "07": ("07-chatbot.json", "json"),
    "05": ("05-assemble.html", "html"),
    "06": (None, "html"),  # output/index.html (여러 장소를 묶는 인덱스라 위치 폴더 밖)
    "08": ("review_result.json", "json"),
}

_JSON_MODELS = {
    "01": Step01VerifyOutput,
    "02": Step02StoryOutput,
    "03": Step03VisualOutput,
    "04": Step04AudioOutput,
    "07": Step07ChatbotOutput,
    "08": Step08ReviewOutput,
}

_HTML_PARSERS = {
    "05": parse_assemble_html,
    "06": parse_map_html,
}


def validate_step(step_id: str, data: Any):
    """data: JSON 스텝이면 dict, HTML 스텝이면 str(HTML 원문).

    성공하면 검증된 모델 인스턴스를 반환한다. 실패하면 SchemaValidationError를
    던지며, 메시지에 어느 필드가 왜 틀렸는지가 전부 들어 있다.
    """
    if step_id in _JSON_MODELS:
        try:
            return _JSON_MODELS[step_id].model_validate(data)
        except ValidationError as exc:
            raise SchemaValidationError(format_validation_error(f"STEP {step_id}", exc)) from exc

    if step_id in _HTML_PARSERS:
        try:
            return _HTML_PARSERS[step_id](data)
        except ValidationError as exc:
            raise SchemaValidationError(format_validation_error(f"STEP {step_id}", exc)) from exc

    raise ValueError(f"알 수 없는 step_id: {step_id!r}")
