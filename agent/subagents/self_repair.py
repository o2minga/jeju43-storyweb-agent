"""self_repair — 08-review에서 status:"fail"로 나온 항목만, 원인이 되는 스텝 하나만
좁게 재실행해서 고친다. "전체를 처음부터 다시 만드는" 재실행이 아니라, 검수가 지적한
문제 문구를 그대로 프롬프트에 얹어 "이 부분만 정확히 고쳐라"고 요청하는 방식이다.

check_id → 책임 스텝 매핑(카드 무관, 항상 동일 — spec.md들이 정의한 각 스텝의 역할에서
그대로 도출):
- 01-source-missing        → 02 (출처를 카드에서 옮기다 놓친 건 보통 02)
- 02-ai-generated-label     → 05 ([연출] 마크업 태깅은 05의 조립 로직 책임)
- 06-chatbot-kb-consistency → 07 (07의 kb[]가 02의 chatbot_kb와 어긋난 것)
- 04-fact-consistency       → 01 또는 02, 이슈 위치로 판단(_targets_for_check 참고):
  이슈가 "02-story.json > conflicts_carried_forward/precision_guardrails_applied"를
  가리키면 02가 01의 내용을 제대로 이어받지 못한 것이고, 05-assemble.html이 01에 없는
  fact_id를 참조하는 경우는 그 fact_id의 출처인 01이 대상이다.

03-fabrication(Claude 판단이라 기계적으로 원인 스텝을 못 정함)·05-terminology(스펙상
항상 needs_human 고정값이라 애초에 fail이 나지 않음) 등 매핑이 없는 check_id는 자동
수복 대상이 아니라 바로 사람 확인 목록(needs_human)으로 넘긴다.

카드 원문(card_text)이 없으면 01/02는 안전하게 재실행할 수 없다(카드 밖 내용을
지어낼 수 없으므로) — 이 경우도 needs_human으로 넘긴다.
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from generate.dispatch import generate_step
from llm_client import LLMCallError
from schema.common import SchemaValidationError
from schema.validate import STEP_FILES, validate_step

logger = logging.getLogger("agent.subagents.self_repair")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = REPO_ROOT / "output"
LOGS_ROOT = REPO_ROOT / "logs"

MAX_ATTEMPTS = 2

_STEP_LABEL = {
    "01": "01-verify(자료 검증)",
    "02": "02-story(이야기 작성)",
    "05": "05-assemble(웹페이지 조립)",
    "07": "07-chatbot(AI 챗봇)",
}

# 이 스텝을 재실행하려면 results에 미리 있어야 하는 이전 스텝들.
_REQUIRED_UPSTREAM = {
    "01": [],
    "02": ["01"],
    "07": ["01", "02"],
    "05": ["01", "02"],
}

# check_id -> 고정 담당 스텝. "04-fact-consistency"는 이슈 내용에 따라 갈리므로
# _targets_for_check()에서 별도 처리한다.
_FIXED_TARGET = {
    "01-source-missing": "02",
    "02-ai-generated-label": "05",
    "06-chatbot-kb-consistency": "07",
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _issue_text(issue: dict) -> str:
    return f"{issue.get('location', '(위치 미상)')}: {issue.get('detail', '')}"


def _targets_for_check(check: dict) -> dict[str, list[str]]:
    """이 fail 항목이 어느 스텝(들)의 책임인지와, 그 스텝에 줄 구체적 지적 사항을 반환한다.
    매핑이 없으면 빈 dict(=자동 수복 불가 → needs_human)."""
    check_id = check["check_id"]
    issues = check.get("issues") or []
    reason = check.get("reason")
    fallback_texts = [_issue_text(i) for i in issues] or [reason or "(구체적 사유 없음)"]

    if check_id in _FIXED_TARGET:
        return {_FIXED_TARGET[check_id]: fallback_texts}

    if check_id == "04-fact-consistency":
        targets: dict[str, list[str]] = {}
        if issues:
            for issue in issues:
                step = "02" if "02-story.json" in issue.get("location", "") else "01"
                targets.setdefault(step, []).append(_issue_text(issue))
        else:
            targets["02"] = fallback_texts
        return targets

    return {}


def _output_path(location_id: str, step_id: str) -> Path:
    filename, _kind = STEP_FILES[step_id]
    if step_id == "06":
        return OUTPUT_ROOT / "index.html"
    return OUTPUT_ROOT / location_id / filename


def _backup_file(location_id: str, step_id: str, tag: str) -> Path | None:
    """수정 전 원본을 output/{location_id}/.backup/{tag}/{파일명}에 복사해 둔다.
    원본이 아직 없으면(첫 생성) 백업할 것도 없으므로 None을 반환한다."""
    src = _output_path(location_id, step_id)
    if not src.exists():
        return None
    backup_dir = OUTPUT_ROOT / location_id / ".backup" / tag
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / src.name
    shutil.copy2(src, dest)
    return dest


def _repair_log_path(location_id: str) -> Path:
    d = LOGS_ROOT / location_id / "repair"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"


def _append_log(log_path: Path, entry: dict) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info("self_repair 기록: %s", entry)


def _load_existing_results(location_id: str) -> dict[str, Any]:
    """results가 주어지지 않았을 때, 디스크에 이미 있는 이전 스텝 산출물을 읽어 채운다."""
    results: dict[str, Any] = {}
    for step_id in ("01", "02", "03", "04", "07"):
        filename, kind = STEP_FILES[step_id]
        path = OUTPUT_ROOT / location_id / filename
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw) if kind == "json" else raw
        try:
            results[step_id] = validate_step(step_id, data)
        except SchemaValidationError:
            continue  # 이미 깨져 있는 이전 산출물은 조용히 건너뛴다 — needs_human이 알아서 걸러냄
    return results


def repair(
    review_result: dict,
    location_id: str,
    *,
    card_text: str | None = None,
    results: dict[str, Any] | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict:
    """08의 review_result.json(을 읽은 dict)에서 status=="fail"인 항목만 골라 원인 스텝을
    좁게 재실행한다.

    card_text: 01/02 재실행에 필요한 카드 원문. 없으면 01/02가 대상인 항목은 자동으로
        시도하지 않고 needs_human으로 넘어간다.
    results: 이미 검증된 이전 스텝 결과(dict[step_id] -> pydantic 모델/HTML 문자열).
        없으면 디스크에서 다시 읽는다(그래도 없는 스텝이 있으면 해당 항목은 needs_human).

    반환: {"attempted": [{"check_ids", "target_step", "attempts", "schema_ok"}, ...],
           "needs_human": [{"check_id", "reason"}, ...], "log_path": str}
    """
    log_path = _repair_log_path(location_id)

    fails = [c for c in review_result.get("checks", []) if c.get("status") == "fail"]
    if not fails:
        logger.info("self_repair: fail 항목이 없어 수복할 게 없습니다.")
        return {"attempted": [], "needs_human": [], "log_path": str(log_path)}

    if results is None:
        results = _load_existing_results(location_id)
    else:
        results = dict(results)  # 호출자의 dict를 직접 변형하지 않는다

    step_jobs: dict[str, dict[str, list[str]]] = {}
    needs_human: list[dict] = []

    for check in fails:
        targets = _targets_for_check(check)
        if not targets:
            reason = "자동 수복 매핑이 없는 항목(Claude 판단이 필요한 항목) — 사람 확인 필요"
            needs_human.append({"check_id": check["check_id"], "reason": reason})
            _append_log(
                log_path,
                {"timestamp": _now_iso(), "check_id": check["check_id"], "target_step": None,
                 "action": "no_mapping", "result": "needs_human", "detail": reason},
            )
            continue
        for step_id, texts in targets.items():
            job = step_jobs.setdefault(step_id, {"check_ids": [], "instructions": []})
            job["check_ids"].append(check["check_id"])
            job["instructions"].append(
                f"### 체크 ID: {check['check_id']}\n" + "\n".join(f"- {t}" for t in texts)
            )

    attempted: list[dict] = []

    for step_id, job in step_jobs.items():
        check_ids_label = ", ".join(job["check_ids"])
        print(f"[repair] {check_ids_label} → {step_id} 재요청 중...")

        missing_upstream = [s for s in _REQUIRED_UPSTREAM.get(step_id, []) if s not in results]
        if missing_upstream:
            reason = f"{step_id} 재실행에 필요한 이전 스텝 결과({', '.join(missing_upstream)})가 없음"
            needs_human.append({"check_id": check_ids_label, "reason": reason})
            _append_log(
                log_path,
                {"timestamp": _now_iso(), "check_ids": job["check_ids"], "target_step": step_id,
                 "action": "skip_missing_upstream", "result": "needs_human", "detail": reason},
            )
            continue

        if step_id in ("01", "02") and card_text is None:
            reason = "카드 원문(card_text)이 없어 01/02를 안전하게 재실행할 수 없음(지어낼 수 없어 건너뜀)"
            needs_human.append({"check_id": check_ids_label, "reason": reason})
            _append_log(
                log_path,
                {"timestamp": _now_iso(), "check_ids": job["check_ids"], "target_step": step_id,
                 "action": "skip_no_card", "result": "needs_human", "detail": reason},
            )
            continue

        extra_instruction = (
            "아래는 이전 실행에서 검수(08-review)가 발견한 문제를 수정하기 위한 좁은 범위의 "
            f"재요청이다. {_STEP_LABEL.get(step_id, step_id)} 전체를 처음부터 새로 쓰지 말고, "
            "아래 지적된 문제만 정확히 고치되 나머지 필드는 원래 의도를 최대한 유지하라.\n\n"
            + "\n\n".join(job["instructions"])
        )

        resolved = False
        last_error: str | None = None
        attempts_used = 0

        for attempt in range(1, max_attempts + 1):
            attempts_used = attempt
            backup_path = _backup_file(location_id, step_id, f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{step_id}-a{attempt}")
            try:
                _path, data = generate_step(step_id, location_id, card_text, results, extra_instruction=extra_instruction)
                validated = validate_step(step_id, data)
            except (LLMCallError, SchemaValidationError) as exc:
                last_error = str(exc)
                _append_log(
                    log_path,
                    {"timestamp": _now_iso(), "check_ids": job["check_ids"], "target_step": step_id,
                     "attempt": attempt, "action": "regenerate", "result": "schema_error",
                     "backup": str(backup_path) if backup_path else None, "error": last_error},
                )
                continue

            results[step_id] = validated if STEP_FILES[step_id][1] == "json" else data
            resolved = True
            _append_log(
                log_path,
                {"timestamp": _now_iso(), "check_ids": job["check_ids"], "target_step": step_id,
                 "attempt": attempt, "action": "regenerate", "result": "schema_ok",
                 "backup": str(backup_path) if backup_path else None, "error": None},
            )
            break

        attempted.append(
            {"check_ids": job["check_ids"], "target_step": step_id, "attempts": attempts_used, "schema_ok": resolved}
        )
        if not resolved:
            reason = f"{max_attempts}회 재시도해도 {step_id} 스키마 검증 실패: {last_error}"
            needs_human.append({"check_id": check_ids_label, "reason": reason})

    return {"attempted": attempted, "needs_human": needs_human, "log_path": str(log_path)}
