"""모든 스텝 스키마가 공유하는 기반 타입과 에러 포맷터.

- StrictModel: 정의되지 않은 필드가 들어오면(스키마 드리프트·오타) 에러가 나도록 extra="forbid",
  그리고 "yes"/1 같은 값이 bool로 조용히 변환되는 등의 느슨한 타입 변환을 막도록 strict=True.
- LangText: {"ko": "...", "en": "..."} 언어 라벨 구조 (여러 스텝 spec.md 공통 패턴).
- format_validation_error / SchemaValidationError: run_agent.py가 "어느 스텝의 어느 필드가
  왜 문제인지"를 사람이 바로 읽을 수 있게 통일된 형태로 출력하기 위한 헬퍼.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LangText(StrictModel):
    ko: str
    en: str


def format_validation_error(step_label: str, exc: ValidationError) -> str:
    lines = [f"{step_label} 스키마 검증 실패 ({exc.error_count()}건):"]
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(root)"
        lines.append(f"  - field: {loc}")
        lines.append(f"    reason: {err['msg']} (type={err['type']})")
    return "\n".join(lines)


class SchemaValidationError(Exception):
    """validate_step()이 던지는, 이미 사람이 읽기 좋게 포맷된 예외."""
