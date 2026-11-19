"""on_complete 시점에 08(검수) 결과를 사람이 읽는 보고서로 남기는 훅.

hooks.fire()의 after_step/on_complete가 넘기는 "status"는 "이 스텝이 스키마에 맞는
결과물을 만들었는가"(구조적 성공)만 볼 뿐, 08의 실제 콘텐츠 판정(overall_status·
needs_human)은 전혀 보지 않는다 — 08이 구조적으로는 "pass"여도 콘텐츠는 HOLD이고
needs_human 체크가 여러 건일 수 있다(실제로 확인됨). 그래서 이 훅은 hook status가
아니라 results["08"] 안의 overall_status·checks[].status를 직접 읽어 판정한다.
"""
from __future__ import annotations

from pathlib import Path

from . import register

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = REPO_ROOT / "output"


def _build_report(location_id: str, review) -> str:
    lines = [f"# 사람 확인 보고서 — {location_id}", ""]

    if review.overall_status != "PASS":
        lines.append(f"## ⚠ 사람 확인 필요 (전체 판정: {review.overall_status})")
    else:
        lines.append(f"## 전체 판정: {review.overall_status}")
    lines.append("")

    needs_human = [c for c in review.checks if c.status == "needs_human"]
    violations = [c for c in review.checks if c.status in ("fail", "blocked")]

    lines.append(f"### 사람 확인이 필요한 항목 ({len(needs_human)}건)")
    if needs_human:
        for c in needs_human:
            detail = c.reason or "; ".join(f"{i.location}: {i.detail}" for i in c.issues) or "(사유 미기재)"
            lines.append(f"- **{c.name}** — {detail}")
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append(f"### 규칙 위반(fail/blocked) 항목 ({len(violations)}건)")
    if violations:
        for c in violations:
            detail = "; ".join(f"{i.location}: {i.detail}" for i in c.issues) or (c.reason or "(사유 미기재)")
            lines.append(f"- **{c.name}** ({c.status}) — {detail}")
    else:
        lines.append("- 없음")
    lines.append("")

    return "\n".join(lines) + "\n"


def _on_complete(location_id: str, results: dict, **_ignored) -> None:
    review = results.get("08")
    if review is None:
        return  # 08까지 못 간 실행(예: --resume-from으로 05에서 멈춤) — 판정할 게 없음

    report = _build_report(location_id, review)
    path = OUTPUT_ROOT / location_id / "human-review-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


register("on_complete", _on_complete)
