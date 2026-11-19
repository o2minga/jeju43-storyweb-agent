"""08-review 출력 스키마 — skills/08-review/spec.md 7장 "① review_result.json"을 반영.

구조적 타입 검증 외에, spec.md 5장의 핵심 규칙(문서 자체가 강조하는 것들)도
model_validator로 함께 강제한다:
- 6개 점검 항목이 전부 있어야 한다 (하나라도 빠지면 "애매하게 생략"과 같으므로 에러).
- missing_required_files가 있으면 overall_status는 반드시 "실행불가".
- needs_human/fail/blocked이 하나라도 있으면 overall_status는 "PASS"일 수 없다.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import model_validator

from .common import StrictModel

REQUIRED_CHECK_IDS = {
    "01-source-missing",
    "02-ai-generated-label",
    "03-fabrication",
    "04-fact-consistency",
    "05-terminology",
    "06-chatbot-kb-consistency",
}


class Issue(StrictModel):
    location: str
    detail: str


class CheckResult(StrictModel):
    check_id: str
    name: str
    status: Literal["pass", "fail", "needs_human", "blocked"]
    issues: List[Issue]
    reason: Optional[str] = None


class Step08ReviewOutput(StrictModel):
    location_id: str
    overall_status: Literal["PASS", "HOLD", "실행불가"]
    checks: List[CheckResult]
    missing_required_files: List[str]
    generated_at: str

    @model_validator(mode="after")
    def _check_business_rules(self):
        if self.missing_required_files:
            if self.overall_status != "실행불가":
                raise ValueError(
                    "missing_required_files가 있으면 overall_status는 반드시 '실행불가'여야 합니다."
                )
            return self

        ids = {c.check_id for c in self.checks}
        missing = REQUIRED_CHECK_IDS - ids
        if missing:
            raise ValueError(f"6개 점검 항목 중 누락됨: {sorted(missing)}")

        statuses = {c.status for c in self.checks}
        if "needs_human" in statuses and self.overall_status == "PASS":
            raise ValueError("needs_human 항목이 있으면 overall_status는 PASS일 수 없습니다.")
        if "fail" in statuses and self.overall_status == "PASS":
            raise ValueError("fail 항목이 있으면 overall_status는 PASS일 수 없습니다.")
        if "blocked" in statuses and self.overall_status == "PASS":
            raise ValueError("blocked 항목이 있으면 overall_status는 PASS일 수 없습니다.")
        return self
