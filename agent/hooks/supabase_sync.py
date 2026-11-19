"""after_step 시점에 05(웹조립)가 구조적으로 성공하면, 실제 HTML 원문을 팀 미리보기용
Supabase locations 테이블에 동기화하는 훅.

이 시점엔 아직 08(검수)이 실행되지 않아 콘텐츠 판정(overall_status: PASS/HOLD)을 알
수 없다 — 그래도 동기화는 그대로 진행한다. 이 미리보기는 팀·함께공이 검토하는
화면이라, 최종 승인 전 콘텐츠가 보이는 게 오히려 목적에 맞는다. 최종 판정 알림은
human_report.py가 따로 맡는다(역할 분리).

dispatch.py의 05 생성 경로도 이미 sync_to_supabase()를 호출하지만, 그건 "05를 새로
생성했을 때"만 실행된다. 이 훅은 "기존 05-assemble.html을 그대로 재사용했을 때"도
미리보기가 최신 상태를 유지하도록 매 실행마다 동작한다 — 두 호출 다 멱등(upsert)이라
겹쳐도 문제는 없다.

주의: hooks.fire()는 콜백 예외를 로그로만 남기고 삼킨다(파이프라인을 막지 않기
위해서) — 즉 이 훅을 통한 Supabase 동기화 실패는 조용히 넘어간다. dispatch.py의
원래 호출(생성 시점)은 여전히 실패 시 예외를 그대로 올린다(step05_assemble.py 참고).
"""
from __future__ import annotations

from pathlib import Path

from generate.step05_assemble import sync_to_supabase

from . import register

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = REPO_ROOT / "output"


def _read_index_html() -> str:
    path = OUTPUT_ROOT / "index.html"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _after_step(step_id: str, location_id: str, status: str, data=None, **_ignored) -> None:
    if step_id != "05" or status != "pass":
        return
    sync_to_supabase(location_id, data, _read_index_html())


register("after_step", _after_step)
