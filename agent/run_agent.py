#!/usr/bin/env python3
"""제주 4·3 스토리웹 에이전트 — 파이프라인 러너: 생성 + 스텝별 스키마 검증.

01→02→03→04→07→05→06→08 순서(AGENT-SPEC.md 4장, 07이 05보다 먼저 끝나야 조립 시
모달을 끼워 넣을 수 있음)로 각 스텝을 처리한다. 스텝별 산출물이 아직 없으면(또는
--force가 주어지면) agent/generate/의 해당 생성기를 호출해 실제로 만든 뒤, 곧바로
agent/schema/의 스키마로 검증한다. 검증에 실패하면 어느 스텝·어느 필드가 문제인지
출력하고 그 자리에서 멈춘다.

01·02(추론형, Claude 실제 호출)와 06(카드 원문에서 좌표를 직접 뽑아야 함)은 생성 시
카드 원문(--card)이 필요하다. 03·04는 아직 Higgsfield/TTS API 키가 없어 결정론적
placeholder로 생성된다(AGENT-SPEC.md 5장 B그룹). 05·06은 Claude를 호출하지 않는
조립형(C그룹) 코드 템플릿이다.

사용법:
    python agent/run_agent.py --location gwandeokjeong --card "test-card/관덕정_카드.md"
    python agent/run_agent.py --location gwandeokjeong --resume-from 05
    python agent/run_agent.py --location gwandeokjeong --card "..." --force
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = REPO_ROOT / "output"

from dotenv import load_dotenv  # noqa: E402

# ANTHROPIC_API_KEY(01/02/07/08), CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN(03),
# SUPABASE_*(05)를 Next.js 쪽과 같은 파일(.env.local)에서 읽어온다 — 이미 켜진 셸
# 환경변수가 있으면 그쪽이 우선한다(override=False, 기본값).
load_dotenv(REPO_ROOT / ".env.local")

import hooks  # noqa: E402
import hooks.human_report  # noqa: E402,F401 - import 자체가 register()를 실행해 훅을 등록한다
import hooks.supabase_sync  # noqa: E402,F401 - 위와 동일
from generate.dispatch import generate_step  # noqa: E402
from llm_client import LLMCallError, get_last_telemetry, reset_telemetry  # noqa: E402
from schema.common import SchemaValidationError  # noqa: E402
from schema.validate import STEP_FILES, validate_step  # noqa: E402

LOGS_ROOT = REPO_ROOT / "logs"

# 같은 스텝 생성이 LLMCallError(claude CLI의 일시적 오류 등 재현 안 되는 실패)로
# 죽으면, 최초 시도 포함 이 횟수까지 자동으로 다시 시도한다(그래도 실패하면 그때
# 멈춘다). SchemaValidationError(콘텐츠·크로스스텝 정합성 문제)는 같은 스텝을
# 다시 돌려도 대개 같은 이유로 또 실패하므로 재시도 대상이 아니다.
MAX_STEP_ATTEMPTS = int(os.environ.get("MAX_STEP_ATTEMPTS", "3"))
STEP_RETRY_DELAY_SEC = float(os.environ.get("STEP_RETRY_DELAY_SEC", "5"))

STEP_ORDER = ["01", "02", "03", "04", "07", "05", "06", "08"]

# 01·02는 카드 원문을 직접 읽어 실제 생성(LLM)한다. 06은 01/02 JSON에는 없는 좌표를
# 카드 원문에서 정규식으로 뽑아야 한다(설계상 알려진 예외 — 요약 3번 항목 참조).
NEEDS_CARD_TEXT = {"01", "02", "06"}

# 실제로 Claude를 호출하는 스텝(나머지 03/04/05/06은 결정론적 placeholder/템플릿).
LLM_STEPS = {"01", "02", "07", "08"}

# 터미널 진행 표시에 쓰는, 데모 영상에 그대로 나와도 이해되는 쉬운 한국어 라벨.
STEP_DISPLAY = {
    "01": "자료 검증",
    "02": "이야기 작성",
    "03": "비주얼·영상 생성",
    "04": "오디오 제작",
    "07": "AI 챗봇 준비",
    "05": "웹페이지 조립",
    "06": "지도 인덱스 생성",
    "08": "최종 검수",
}

# STEP_ORDER 안에서의 위치(1~8) — --resume-from으로 중간부터 시작해도 "몇 번째 스텝"인지
# 항상 실제 파이프라인 순서 기준으로 보여주기 위함.
_STEP_POSITION = {step_id: i + 1 for i, step_id in enumerate(STEP_ORDER)}
_TOTAL_STEPS = len(STEP_ORDER)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _completion_detail(step_id: str, validated) -> str:
    """스텝별 특성에 맞는 완료 메시지 — 데모에서 "지금 뭘 만들었는지"가 바로 보이게."""
    if step_id == "01":
        return f"사실 {len(validated.verified_facts)}건, 출처 {len(validated.sources)}건 확인됨"
    if step_id == "02":
        return f"원고 생성, 타임라인 {len(validated.timeline_events)}건"
    if step_id == "03":
        s = validated.gate_summary
        return f"이미지·영상 {s.total}건 생성 (통과 {s.passed}, 대체 {s.converted}, 생략 {s.skipped})"
    if step_id == "04":
        narration_state = "내레이션 생성됨" if validated.narration is not None else "내레이션 없음(원고 없음)"
        return f"{narration_state}, 배경음악(BGM) 준비 완료"
    if step_id == "07":
        return f"챗봇 지식베이스 {len(validated.kb)}건 준비"
    if step_id == "05":
        return "조립 완료"
    if step_id == "06":
        return f"지도에 장소 {len(validated.markers)}곳 표시"
    if step_id == "08":
        return f"판정 결과: {validated.overall_status}"
    return "완료"


def _make_run_dir(location_id: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = LOGS_ROOT / location_id / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


class _RunLogger:
    """스텝별 상세 기록(steps.jsonl)과 전체 요약(run-summary.json)을 남긴다.

    LLM을 실제로 부른 스텝(need_generate=True 이면서 LLM_STEPS에 속함)만
    get_last_telemetry()의 실측치를 쓴다 — 그 외(결정론적 스텝, 파일 재사용)는
    이전 스텝의 수치가 새어 들어간 것처럼 보이지 않도록 "N/A" 계열 문구로 남긴다.
    """

    def __init__(self, location_id: str):
        self.run_dir = _make_run_dir(location_id)
        self.steps_log_path = self.run_dir / "steps.jsonl"
        self.started_at = _now_iso()
        self._start = time.monotonic()
        self.records: list[dict] = []

    def _build_entry(self, step_id: str, need_generate: bool, status: str, error: str | None) -> dict:
        telemetry = get_last_telemetry()
        llm_actually_called = step_id in LLM_STEPS and need_generate and telemetry.attempts > 0

        if llm_actually_called:
            return {
                "timestamp": _now_iso(),
                "step_id": step_id,
                "step_name": STEP_DISPLAY[step_id],
                "status": status,
                "attempts": telemetry.attempts,
                "prompt_summary": telemetry.prompt_preview,
                "response_summary": telemetry.response_preview,
                "input_tokens": telemetry.input_tokens,
                "output_tokens": telemetry.output_tokens,
                "cost_usd": telemetry.cost_usd,
                "duration_sec": telemetry.duration_sec,
                "tool_calls": telemetry.tool_calls,
                "error": error,
            }

        if step_id not in LLM_STEPS:
            note = "규칙 기반 생성 — LLM 호출 없음"
        elif not need_generate:
            note = "기존 파일 재사용 — 이번 실행에는 LLM 호출 없음"
        else:
            note = "LLM 호출 없이 완료됨(내부 로직에서 생략)"

        return {
            "timestamp": _now_iso(),
            "step_id": step_id,
            "step_name": STEP_DISPLAY[step_id],
            "status": status,
            "attempts": None,
            "prompt_summary": note,
            "response_summary": note,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "duration_sec": None,
            "tool_calls": [],
            "error": error,
        }

    def record(self, step_id: str, need_generate: bool, status: str, error: str | None = None) -> None:
        entry = self._build_entry(step_id, need_generate, status, error)
        with self.steps_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.records.append(entry)

    def write_summary(self) -> None:
        elapsed = round(time.monotonic() - self._start, 3)
        summary = {
            "started_at": self.started_at,
            "finished_at": _now_iso(),
            "total_duration_sec": elapsed,
            "total_input_tokens": sum(r["input_tokens"] or 0 for r in self.records),
            "total_output_tokens": sum(r["output_tokens"] or 0 for r in self.records),
            "total_cost_usd": round(sum(r["cost_usd"] or 0 for r in self.records), 4),
            "any_retry": any((r["attempts"] or 0) > 1 for r in self.records),
            "steps": [
                {
                    "step_id": r["step_id"],
                    "step_name": r["step_name"],
                    "status": r["status"],
                    "retried": (r["attempts"] or 0) > 1,
                }
                for r in self.records
            ],
        }
        (self.run_dir / "run-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _resolve_path(step_id: str, location_id: str) -> Path:
    filename, _kind = STEP_FILES[step_id]
    if step_id == "06":
        return OUTPUT_ROOT / "index.html"
    return OUTPUT_ROOT / location_id / filename


def _load(step_id: str, location_id: str):
    _filename, kind = STEP_FILES[step_id]
    path = _resolve_path(step_id, location_id)

    if not path.exists():
        raise FileNotFoundError(str(path))

    if kind == "json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SchemaValidationError(f"STEP {step_id} ({path}) JSON 파싱 실패: {exc}") from exc
        return path, data

    return path, path.read_text(encoding="utf-8")


def _read_card_text(card_arg: str | None) -> str | None:
    if not card_arg:
        return None
    path = Path(card_arg)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.read_text(encoding="utf-8")


def _preload(step_id: str, location_id: str, results: dict) -> int | None:
    """--resume-from 앞쪽 스텝들을 디스크에서 읽어 results에 채운다. 실패하면 종료 코드를 반환."""
    _filename, kind = STEP_FILES[step_id]
    try:
        _path, data = _load(step_id, location_id)
    except FileNotFoundError as exc:
        print(f"--resume-from 을 쓰려면 이전 스텝 {step_id}의 출력이 먼저 있어야 합니다 — {exc}", file=sys.stderr)
        return 2
    try:
        validated = validate_step(step_id, data)
    except SchemaValidationError as exc:
        print(str(exc))
        print(f"\n이전 스텝 {step_id} 검증 실패 — 재개할 수 없습니다.")
        return 1
    results[step_id] = validated if kind == "json" else data
    return None


def run(location_id: str, card_arg: str | None, resume_from: str | None, force: bool, repair: bool = False) -> int:
    steps = STEP_ORDER
    preload_steps: list[str] = []
    if resume_from:
        if resume_from not in steps:
            print(f"알 수 없는 --resume-from 값: {resume_from!r} (선택 가능: {steps})", file=sys.stderr)
            return 2
        idx = steps.index(resume_from)
        preload_steps, steps = steps[:idx], steps[idx:]

    try:
        card_text = _read_card_text(card_arg)
    except OSError as exc:
        print(f"--card 파일을 읽을 수 없습니다: {exc}", file=sys.stderr)
        return 2

    results: dict = {}
    for step_id in preload_steps:
        code = _preload(step_id, location_id, results)
        if code is not None:
            return code

    rlog = _RunLogger(location_id)

    def _after_step(
        step_id: str, need_generate: bool, status: str, result=None, data=None, error: str | None = None
    ) -> None:
        hooks.fire(
            "after_step",
            step_id=step_id,
            location_id=location_id,
            need_generate=need_generate,
            status=status,
            result=result,
            data=data,
            error=error,
        )

    for step_id in steps:
        idx = _STEP_POSITION[step_id]
        label = STEP_DISPLAY[step_id]
        hooks.fire("before_step", step_id=step_id, location_id=location_id, index=idx, total=_TOTAL_STEPS)
        print(f"[{idx:02d}/{_TOTAL_STEPS}] {label} 시작...")

        _filename, kind = STEP_FILES[step_id]
        path = _resolve_path(step_id, location_id)
        need_generate = force or not path.exists()
        reset_telemetry()

        if need_generate:
            if step_id in NEEDS_CARD_TEXT and card_text is None:
                msg = "생성하려면 --card 옵션으로 유적지 카드 경로를 지정해야 합니다."
                print(f"[{idx:02d}/{_TOTAL_STEPS}] 실패 — {msg}")
                rlog.record(step_id, need_generate, "fail", msg)
                _after_step(step_id, need_generate, "fail", error=msg)
                rlog.write_summary()
                return 2
            last_error: LLMCallError | None = None
            for attempt in range(1, MAX_STEP_ATTEMPTS + 1):
                try:
                    path, data = generate_step(step_id, location_id, card_text, results)
                    last_error = None
                    break
                except LLMCallError as exc:
                    last_error = exc
                    if attempt < MAX_STEP_ATTEMPTS:
                        print(
                            f"[{idx:02d}/{_TOTAL_STEPS}] 일시적 오류 — {exc} "
                            f"({attempt}/{MAX_STEP_ATTEMPTS}회 시도 실패, {STEP_RETRY_DELAY_SEC}초 후 재시도)"
                        )
                        time.sleep(STEP_RETRY_DELAY_SEC)
                        reset_telemetry()

            if last_error is not None:
                msg = f"생성 중 오류 — {MAX_STEP_ATTEMPTS}회 시도 모두 실패: {last_error}"
                print(f"[{idx:02d}/{_TOTAL_STEPS}] 실패 — {msg}")
                rlog.record(step_id, need_generate, "fail", msg)
                _after_step(step_id, need_generate, "fail", error=msg)
                rlog.write_summary()
                return 1
        else:
            try:
                path, data = _load(step_id, location_id)
            except FileNotFoundError as exc:
                msg = f"출력 파일이 없습니다 — {exc}"
                print(f"[{idx:02d}/{_TOTAL_STEPS}] 실패 — {msg}")
                rlog.record(step_id, need_generate, "fail", msg)
                _after_step(step_id, need_generate, "fail", error=msg)
                rlog.write_summary()
                return 1
            except SchemaValidationError as exc:
                msg = str(exc)
                print(msg)
                print(f"[{idx:02d}/{_TOTAL_STEPS}] 실패 — 기존 파일 검증 실패")
                rlog.record(step_id, need_generate, "fail", msg)
                _after_step(step_id, need_generate, "fail", error=msg)
                rlog.write_summary()
                return 1

        try:
            validated = validate_step(step_id, data)
        except SchemaValidationError as exc:
            msg = str(exc)
            rel = path.relative_to(REPO_ROOT)
            print(msg)
            print(f"[{idx:02d}/{_TOTAL_STEPS}] 실패 — 스키마 검증 실패 ({rel})")
            rlog.record(step_id, need_generate, "fail", msg)
            _after_step(step_id, need_generate, "fail", data=data, error=msg)
            rlog.write_summary()
            return 1

        results[step_id] = validated if kind == "json" else data
        rlog.record(step_id, need_generate, "pass")
        _after_step(step_id, need_generate, "pass", result=validated, data=data)

        detail = _completion_detail(step_id, validated)
        origin_label = "새로 생성" if need_generate else "기존 결과 재사용"
        print(f"[{idx:02d}/{_TOTAL_STEPS}] 완료 ({origin_label}) — {detail}")

    print(f"\n'{location_id}': {len(steps)}개 스텝 전부 생성/검증 통과.")

    if repair and "08" in results:
        _run_repair(location_id, card_text, results)

    hooks.fire("on_complete", location_id=location_id, results=results)

    rlog.write_summary()
    print(f"실행 기록: {rlog.run_dir.relative_to(REPO_ROOT)}")
    return 0


def _run_repair(location_id: str, card_text: str | None, results: dict) -> None:
    """--repair가 켜져 있을 때만 호출된다 — 08 결과에 fail이 있으면 self_repair로 좁게
    고친 뒤, 08을 다시 실행해 fail이 실제로 해소됐는지 재확인한다. --repair를 안 켜면
    이 함수 자체가 호출되지 않으므로 기존 동작에는 전혀 영향이 없다."""
    import subagents.self_repair as self_repair

    step08_result = results["08"]
    fail_checks = [c for c in step08_result.checks if c.status == "fail"]
    if not fail_checks:
        print("\n[repair] 검수 결과 fail 없음 — 수복할 게 없습니다.")
        return

    print(f"\n[repair] 검수(08) 결과 fail {len(fail_checks)}건 발견 — 자동 수복을 시도합니다.")
    review_dict = step08_result.model_dump(mode="json")
    outcome = self_repair.repair(review_dict, location_id, card_text=card_text, results=results)

    for a in outcome["attempted"]:
        status_kr = "스키마 검증 통과" if a["schema_ok"] else "스키마 검증 실패"
        print(
            f"[repair] {', '.join(a['check_ids'])} → {a['target_step']} 재요청 완료 "
            f"({a['attempts']}회 시도, {status_kr})"
        )
    for nh in outcome["needs_human"]:
        print(f"[repair] {nh['check_id']} → 자동 수복 불가, 사람 확인 필요 — {nh['reason']}")

    print("[repair] 08 재검수 중...")
    try:
        _path, data = generate_step("08", location_id, card_text, results)
        validated = validate_step("08", data)
    except (LLMCallError, SchemaValidationError) as exc:
        print(f"[repair] 08 재검수 실패 — {exc}")
        return

    results["08"] = validated
    new_fail_count = len([c for c in validated.checks if c.status == "fail"])
    print(
        f"[repair] 재검수 결과: 판정 {validated.overall_status} "
        f"(fail {len(fail_checks)}건 → {new_fail_count}건)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jeju 4.3 storyweb agent runner — 스텝별로 없는 산출물은 생성하고, 있으면 검증만 한다."
    )
    parser.add_argument("--location", help="output/{location_id}/ 의 location_id (예: gwandeokjeong)")
    parser.add_argument("--card", help="유적지 카드(.md) 경로 — 01/02/06 생성에 필요")
    parser.add_argument("--resume-from", help="이 스텝부터 처리한다 (예: 05)")
    parser.add_argument(
        "--force", action="store_true", help="이미 파일이 있어도 다시 생성한다(기본은 있으면 재사용)"
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="08 검수에서 fail이 나오면 원인 스텝만 좁게 재요청해 자동 수복을 시도한다(기본은 off — 안 켜면 기존 동작과 동일)",
    )
    args = parser.parse_args()

    if not args.location:
        print(
            "사용법: run_agent.py --location <location_id> [--card <path>] [--resume-from 05] [--force] [--repair]",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(run(args.location, args.card, args.resume_from, args.force, args.repair))


if __name__ == "__main__":
    main()
