"""03-visual 출력 스키마 — skills/03-visual/spec.md 6장(출력 형식)을 그대로 반영.

gate_summary와 assets의 개수가 서로 어긋나면(집계 실수) 구조적으로는 유효해도
내용이 틀린 것이므로, 모델 검증 시 함께 대조한다.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import model_validator

from .common import LangText, StrictModel


class VisualAsset(StrictModel):
    asset_id: str
    source_prompt_id: str
    type: Literal["image", "video", "archival"]
    path: str
    duration_sec: Optional[float] = None  # video일 때만 등장 (그 외 자산은 키 자체 생략 가능)
    is_ai_generated: bool
    label: str = ""  # 문헌 이미지는 없음/빈값
    gate: Literal["passed", "converted", "skipped"]
    gate_reason: str
    final_prompt: Optional[str]  # archival이면 null — 키 자체는 항상 있어야 함
    source: str
    caption: LangText
    # 반자동 워크플로우(관리자가 assets/{location_id}/{prompt_id}.{ext}에 실제 파일을 직접
    # 넣는 방식)의 진행 상태. path에 파일이 이미 있으면 "ready", 없으면
    # "awaiting_manual_generation". 이 필드가 아예 없던 구식 03-visual.json(이 필드를
    # 추가하기 전에 생성된 파일)을 읽을 때도 반드시 "awaiting_manual_generation"으로
    # 채워야 한다 — "사람이 아직 안 만든 이미지"를 실수로 ready로 오인하면 05가 없는
    # 파일을 그대로 조립하거나 08이 검수를 잘못 통과시킬 수 있으므로, 애매하면 항상
    # "아직 준비 안 됨" 쪽을 기본값으로 삼는다(None으로 두지 않는다).
    status: Literal["awaiting_manual_generation", "ready"] = "awaiting_manual_generation"


class GateSummary(StrictModel):
    total: int
    passed: int
    converted: int
    skipped: int
    note: str


class Step03VisualOutput(StrictModel):
    location_id: str
    art_style_ref: str
    assets: List[VisualAsset]
    gate_summary: GateSummary

    @model_validator(mode="after")
    def _check_gate_summary_matches_assets(self):
        s = self.gate_summary
        if s.total != len(self.assets):
            raise ValueError(
                f"gate_summary.total({s.total})이 assets 개수({len(self.assets)})와 다릅니다."
            )
        counted = {"passed": 0, "converted": 0, "skipped": 0}
        for a in self.assets:
            counted[a.gate] += 1
        for key in counted:
            if getattr(s, key) != counted[key]:
                raise ValueError(
                    f"gate_summary.{key}({getattr(s, key)})가 실제 assets 집계({counted[key]})와 다릅니다."
                )
        return self
