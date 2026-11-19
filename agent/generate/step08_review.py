"""08-review 실제 생성.

spec.md 4장이 정의한 6개 점검 중 ①②④⑥은 "방법"이 이미 기계적으로 정의돼 있다 —
05-assemble.html의 data-source/data-fact-id, class="ai-generated" 캡션, 01/02/07의
JSON을 코드로 직접 대조하면 되는 항목들이다. 그래서 이 넷은 Claude를 부르지 않고
코드로 직접 파싱·대조한다(재현성 확보 — spec.md 5장 "같은 입력이면 같은 결과").

③지어내기 여부만 실제로 Claude 판단이 필요하다(의역·우회 서술은 키워드 대조로 못 잡는다는
spec.md 자신의 한계 인정 때문). ⑤용어 풀이 여부는 spec.md 자신이 "원칙적으로 항상
needs_human으로 분류한다"고 못 박아 두었으므로, 이 역시 Claude를 부를 필요 없이
고정값이다. 결과적으로 이 파일에서 Claude를 부르는 곳은 ③ 하나뿐이다.

overall_status는 Claude가 정하지 않는다 — 6개 check의 status를 코드가 집계해서
결정한다(Step08ReviewOutput의 model_validator와 같은 규칙: needs_human/fail/blocked이
하나라도 있으면 PASS 불가 → missing_required_files가 없다면 남는 선택지는 HOLD뿐).

사람이 읽는 출처 대장(source-ledger.md)·검수 요약(review-summary.md)은 검증된
review_result.json으로부터 결정론적 코드로 템플릿화한다.

필수 파일(01/02/07/05) 중 하나라도 없으면 아무것도 검사하지 않고 즉시 실행불가로
단락한다 — spec.md 2장의 "필수 파일 없으면 나머지 점검을 절대 진행하지 않는다" 규칙.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bs4 import BeautifulSoup

from agents.review_agent import ReviewAgent
from schema.step01_verify import Step01VerifyOutput
from schema.step02_story import Step02StoryOutput
from schema.step03_visual import Step03VisualOutput
from schema.step04_audio import Step04AudioOutput
from schema.step07_chatbot import Step07ChatbotOutput
from schema.step08_review import CheckResult, Issue, Step08ReviewOutput


def generate(
    location_id: str,
    step01: Step01VerifyOutput | None,
    step02: Step02StoryOutput | None,
    step03: Step03VisualOutput | None,
    step04: Step04AudioOutput | None,
    assemble_html: str | None,
    map_html: str | None,
    step07: Step07ChatbotOutput | None,
) -> Step08ReviewOutput:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat()

    missing = []
    if step01 is None:
        missing.append("01-verify.json")
    if step02 is None:
        missing.append("02-story.json")
    if step07 is None:
        missing.append("07-chatbot.json")
    if not assemble_html:
        missing.append("05-assemble.html")

    if missing:
        return Step08ReviewOutput(
            location_id=location_id,
            overall_status="실행불가",
            checks=[],
            missing_required_files=missing,
            generated_at=generated_at,
        )

    media_is_placeholder = (
        step03 is None
        or step04 is None
        # 03은 반자동 워크플로우다 — 관리자가 assets/{location_id}/{prompt_id}.{ext}에
        # 실제 파일을 넣기 전까지 AI 생성 자산의 status는 "ready"가 아니다.
        or any(a.status != "ready" for a in step03.assets if a.is_ai_generated)
        or (step04.narration is not None and step04.narration.source.startswith("AI TTS (placeholder"))
    )
    verified_fact_ids = {f.fact_id for f in step01.verified_facts}

    checks = [
        _check_source_missing(assemble_html, verified_fact_ids),
        _check_ai_generated_label(assemble_html, media_is_placeholder),
        _check_fabrication(step01, step02, assemble_html),
        _check_fact_consistency(assemble_html, step01, step02, verified_fact_ids),
        _check_terminology(),
        _check_chatbot_kb_consistency(step02, step07),
    ]

    return Step08ReviewOutput(
        location_id=location_id,
        overall_status=_compute_overall_status(checks),
        checks=checks,
        missing_required_files=[],
        generated_at=generated_at,
    )


def _compute_overall_status(checks: list[CheckResult]) -> str:
    statuses = {c.status for c in checks}
    if statuses & {"fail", "needs_human", "blocked"}:
        return "HOLD"
    return "PASS"


# --- ① 출처 누락 여부 (코드 파싱) -------------------------------------------------


def _fact_spans(assemble_html: str):
    soup = BeautifulSoup(assemble_html, "html.parser")
    return soup.select(".fact")


def _check_source_missing(assemble_html: str, verified_fact_ids: set[str]) -> CheckResult:
    issues: list[Issue] = []
    for el in _fact_spans(assemble_html):
        fact_id = el.get("data-fact-id", "")
        source = el.get("data-source", "")
        location = f"data-fact-id={fact_id or '(없음)'}"
        if not source:
            issues.append(Issue(location=location, detail='class="fact" 요소에 data-source가 없습니다.'))
        if not fact_id:
            issues.append(Issue(location=f"data-source={source or '(없음)'}", detail="class=\"fact\" 요소에 data-fact-id가 없습니다."))
        elif fact_id not in verified_fact_ids:
            issues.append(Issue(location=location, detail="01-verify.json의 verified_facts에 존재하지 않는 fact_id를 참조합니다."))

    status = "fail" if issues else "pass"
    return CheckResult(check_id="01-source-missing", name="출처 누락 여부", status=status, issues=issues)


# --- ② [연출] 표시 여부 (코드 파싱) ------------------------------------------------


def _check_ai_generated_label(assemble_html: str, media_is_placeholder: bool) -> CheckResult:
    if media_is_placeholder:
        return CheckResult(
            check_id="02-ai-generated-label",
            name="[연출] 표시 여부",
            status="needs_human",
            issues=[],
            reason="관리자가 아직 만들지 않은 이미지가 있음(03-image-prompts-for-admin.md 참고) — 실제 자산 생성 후 재검수 필요",
        )

    soup = BeautifulSoup(assemble_html, "html.parser")
    issues: list[Issue] = []
    for fig in soup.select("figure.ai-generated"):
        caption = fig.find("figcaption")
        caption_text = caption.get_text() if caption else ""
        if "[연출]" not in caption_text:
            origin = fig.get("data-origin", "(알 수 없음)")
            issues.append(Issue(location=f'figure[data-origin="{origin}"]', detail="figcaption에 [연출] 표시가 없습니다."))

    status = "fail" if issues else "pass"
    return CheckResult(check_id="02-ai-generated-label", name="[연출] 표시 여부", status=status, issues=issues)


# --- ④ 사실 일치 여부 (코드 파싱) --------------------------------------------------


def _check_fact_consistency(
    assemble_html: str,
    step01: Step01VerifyOutput,
    step02: Step02StoryOutput,
    verified_fact_ids: set[str],
) -> CheckResult:
    issues: list[Issue] = []

    seen_unknown = set()
    for el in _fact_spans(assemble_html):
        fact_id = el.get("data-fact-id", "")
        if fact_id and fact_id not in verified_fact_ids and fact_id not in seen_unknown:
            seen_unknown.add(fact_id)
            issues.append(
                Issue(location=f"data-fact-id={fact_id}", detail="05-assemble.html이 01-verify.json에 없는 fact_id를 참조합니다.")
            )

    carried_topics = {c.topic for c in step02.conflicts_carried_forward}
    for conflict in step01.conflicts:
        if conflict.topic not in carried_topics:
            issues.append(
                Issue(
                    location="02-story.json > conflicts_carried_forward",
                    detail=f"01의 충돌 항목 '{conflict.topic}'이 02에 반영되지 않았습니다.",
                )
            )

    applied_topics = {g.topic for g in step02.precision_guardrails_applied}
    for guardrail in step01.precision_guardrails:
        if guardrail.topic not in applied_topics:
            issues.append(
                Issue(
                    location="02-story.json > precision_guardrails_applied",
                    detail=f"01의 정밀도 가드레일 '{guardrail.topic}'이 02에 반영되지 않았습니다.",
                )
            )

    status = "fail" if issues else "pass"
    return CheckResult(check_id="04-fact-consistency", name="사실 일치 여부", status=status, issues=issues)


# --- ⑤ 용어 풀이 여부 (spec.md 자체 규정 — 항상 needs_human, 고정값) ------------------


def _check_terminology() -> CheckResult:
    return CheckResult(
        check_id="05-terminology",
        name="용어 풀이 여부",
        status="needs_human",
        issues=[],
        reason="용어 풀이 여부는 spec.md 규칙상 원칙적으로 항상 needs_human으로 분류함",
    )


# --- ⑥ AI 챗봇 지식베이스 일치 여부 (코드 파싱) -------------------------------------


def _check_chatbot_kb_consistency(step02: Step02StoryOutput, step07: Step07ChatbotOutput) -> CheckResult:
    issues: list[Issue] = []

    kb02_ids = {e.qa_id for e in step02.chatbot_kb}
    test_ids = {e.qa_id for e in step02.chatbot_kb if e.note_for_07}
    normal_ids = kb02_ids - test_ids
    kb07_ids = {e.qa_id for e in step07.kb}

    for qa_id in sorted(normal_ids - kb07_ids):
        issues.append(
            Issue(location=f"07-chatbot.json > kb[qa_id={qa_id}]", detail="02의 실제 사실 KB 항목이 07의 kb[]에서 임의로 빠졌습니다.")
        )

    for qa_id in sorted(kb07_ids - kb02_ids):
        issues.append(
            Issue(location=f"07-chatbot.json > kb[qa_id={qa_id}]", detail="02-story.json의 chatbot_kb에 없는 항목이 07의 kb[]에 새로 생겼습니다.")
        )

    for qa_id in sorted(test_ids & kb07_ids):
        issues.append(
            Issue(
                location=f"07-chatbot.json > kb[qa_id={qa_id}]",
                detail="가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.",
            )
        )

    status = "fail" if issues else "pass"
    return CheckResult(check_id="06-chatbot-kb-consistency", name="AI 챗봇 지식베이스 일치 여부", status=status, issues=issues)


# --- ③ 지어내기 여부 (Claude 판단 — 의역·우회 서술은 키워드 대조로 못 잡음) -----------


def _check_fabrication(step01: Step01VerifyOutput, step02: Step02StoryOutput, assemble_html: str) -> CheckResult:
    user_content = (
        "아래는 08-review의 6개 점검 중 ③ '지어내기 여부' 딱 하나만 판정하는 요청이다. "
        "spec.md 4장 ③의 방법을 그대로 따르라: forbidden_topics 핵심 문구가 본문에 그대로 "
        "등장하면 fail. 키워드가 안 보여도 문장 수가 많거나 서술이 구체적인 구간이 있으면 "
        "needs_human으로 분류하고 그 구간을 issues에 위치와 함께 남겨라. 이 항목은 절대 "
        "pass만으로 끝내지 마라 — 사람이 한 번 더 읽어야 할 구간이 있으면 반드시 남겨라. "
        'check_id는 정확히 "03-fabrication", name은 정확히 "지어내기 여부"로 채워라. '
        "status는 pass/fail/needs_human 중 하나만 써라(blocked는 이 판정에 해당하지 않는다).\n\n"
        f"## 01-verify.forbidden_topics\n{step01.forbidden_topics}\n\n"
        f"## 02-story.forbidden_topics\n{step02.forbidden_topics}\n\n"
        f"## 05-assemble.html\n{assemble_html}"
    )
    verdict = ReviewAgent().run(user_content)
    return CheckResult(
        check_id="03-fabrication",
        name="지어내기 여부",
        status=verdict.status,
        issues=verdict.issues,
        reason=verdict.reason,
    )


# --- 사람이 읽는 문서 템플릿 (결정론적) ---------------------------------------------


def _fact_id_referenced(assemble_html: str, fact_id: str) -> bool:
    return f'data-fact-id="{fact_id}"' in assemble_html


def build_source_ledger_md(
    location_name_ko: str,
    step01: Step01VerifyOutput,
    step03: Step03VisualOutput | None,
    assemble_html: str,
) -> str:
    complete_rows = []
    incomplete_rows = []

    for fact in step01.verified_facts:
        if fact.source.type not in ("card", "search"):
            continue
        content, source = fact.text, fact.source.ref
        used_at = "05-assemble.html 본문" if _fact_id_referenced(assemble_html, fact.fact_id) else ""
        if content and source and used_at:
            complete_rows.append((content, source, used_at))
        else:
            incomplete_rows.append((fact.fact_id, content, source, used_at or "(05 본문에서 참조 확인 안 됨)"))

    if step03:
        for asset in step03.assets:
            if asset.is_ai_generated:
                continue  # AI 생성물은 대장 제외 (spec.md 6장)
            content, source = asset.caption.ko, asset.source
            used_at = "05-assemble.html 비주얼 섹션"
            if content and source:
                complete_rows.append((content, source, used_at))
            else:
                incomplete_rows.append((asset.asset_id, content, source, used_at))

    lines = [f"# 출처 대장 — {location_name_ko}", "", "| 내용 | 출처 | 사용 위치 |", "|---|---|---|"]
    for content, source, used_at in complete_rows:
        lines.append(f"| {content} | {source} | {used_at} |")

    lines += ["", "## 출처 정보 불완전 항목 (확인 필요)"]
    if incomplete_rows:
        for item_id, content, source, used_at in incomplete_rows:
            lines.append(f"- [{item_id}] 내용: {content or '(비어있음)'} / 출처: {source or '(비어있음)'} / 사용위치: {used_at}")
    else:
        lines.append("- 없음")

    return "\n".join(lines) + "\n"


def build_review_summary_md(location_name_ko: str, review: Step08ReviewOutput) -> str:
    passed = [c for c in review.checks if c.status == "pass"]
    needs_human = [c for c in review.checks if c.status == "needs_human"]
    failed = [c for c in review.checks if c.status == "fail"]
    blocked = [c for c in review.checks if c.status == "blocked"]

    lines = [f"# 검수 요약 — {location_name_ko}", "", f"**전체 상태**: {review.overall_status}", ""]

    lines.append("## 자동 통과 항목")
    lines += [f"- {c.name}: pass" for c in passed] or ["- 없음"]
    lines.append("")

    lines.append("## 사람 확인이 필요한 항목")
    if needs_human:
        for c in needs_human:
            detail = c.reason or "; ".join(f"{i.location}: {i.detail}" for i in c.issues) or "(사유 미기재)"
            lines.append(f"- {c.name}: {detail}")
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("## 규칙 위반 발견 항목")
    if failed or blocked:
        for c in failed + blocked:
            detail = "; ".join(f"{i.location}: {i.detail}" for i in c.issues) or (c.reason or "(사유 미기재)")
            lines.append(f"- {c.name} ({c.status}): {detail}")
    else:
        lines.append("- 없음")
    lines.append("")

    lines.append("## 다음 단계")
    if review.overall_status == "실행불가":
        lines.append("- 누락된 필수 파일부터 생성한 뒤 08-review를 다시 실행하라: " + ", ".join(review.missing_required_files))
    elif needs_human or failed:
        priority = [c.name for c in failed] + [c.name for c in needs_human]
        lines.append("- 아래 순서로 사람 확인이 필요하다: " + " → ".join(priority))
    else:
        lines.append("- 추가 조치 없음 — 전체 통과")

    return "\n".join(lines) + "\n"
