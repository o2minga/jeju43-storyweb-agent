"""03-visual 실제 생성 — Group B(미디어 생성형).

VisualAgent(agent/agents/visual_agent.py)가 재현 금지 게이트를 통과·변환시킨 최종
프롬프트로 Cloudflare Workers AI(flux-1-schnell)를 호출해 이미지를 실제로 생성한다.
미설정/실패 시에만 관리자가 assets/{location_id}/{prompt_id}.png에 직접 넣은 파일로
폴백한다(VisualAgent 클래스 docstring의 1→4 순서 참고). 이 모듈은 그 결과(record)를
받아 gate 판정과 함께 VisualAsset으로 조립하는 역할만 한다.
"""
from __future__ import annotations

from agents.visual_agent import VisualAgent
from schema.step02_story import Step02StoryOutput
from schema.step03_visual import GateSummary, Step03VisualOutput, VisualAsset

_visual_agent = VisualAgent()


def _build_asset(location_id: str, index: int, prompt) -> VisualAsset:
    asset_id = f"vis-{index:02d}"
    image_prompt = (
        f"장면: {prompt.scene.ko}\n분위기: {prompt.mood}\n03에게 주는 지시: {prompt.note_for_03}"
    )
    result = _visual_agent.generate_asset(prompt.prompt_id, location_id, image_prompt, ext="png")
    gate = result["gate"]
    gate_reason = result["gate_reason"]
    record = result["record"]

    caption_ko = prompt.scene.ko if gate == "passed" else f"{prompt.scene.ko}(우회 연출)"
    if "[연출]" not in caption_ko:
        caption_ko = f"{caption_ko} [연출]"

    if record:
        path = record["target_path"]
        final_prompt = record["final_prompt"]
        status = record["status"]
        generated_by = record.get("generated_by")
        if generated_by == "cloudflare-workers-ai":
            source = "AI 생성 (Cloudflare Workers AI, flux-1-schnell)"
        elif generated_by in ("existing-file", "manual-legacy-copy"):
            source = "AI 생성 (관리자가 외부 도구로 직접 생성)"
        else:
            source = "AI 생성 (관리자 생성 대기 중 — 03-image-prompts-for-admin.md 참고)"
    else:
        # gate == "skipped" — 상징적 대체안도 없어 만들 프롬프트 자체가 없는 경우. 만들
        # 프롬프트도 없으니 당연히 파일도 없다 — "awaiting_manual_generation"으로 둔다.
        path = f"assets/{location_id}/{prompt.prompt_id}.png"
        final_prompt = None
        status = "awaiting_manual_generation"
        source = "AI 생성 보류 (게이트에서 상징적 대체안 없이 포기 — 사람 확인 필요)"

    return VisualAsset(
        asset_id=asset_id,
        source_prompt_id=prompt.prompt_id,
        type="image",
        path=path,
        duration_sec=None,
        is_ai_generated=True,
        label="[연출]",
        gate=gate,
        gate_reason=gate_reason,
        final_prompt=final_prompt,
        source=source,
        caption={"ko": caption_ko, "en": ""},
        status=status,
    )


def generate(location_id: str, step02: Step02StoryOutput) -> Step03VisualOutput:
    drafts = step02.image_prompts_draft
    if not drafts:
        return Step03VisualOutput(
            location_id=location_id,
            art_style_ref="skills/03-visual/art-style.md",
            assets=[],
            gate_summary=GateSummary(total=0, passed=0, converted=0, skipped=0, note="image_prompts_draft가 비어 있어 자산을 만들지 않음"),
        )

    assets = [_build_asset(location_id, i, draft) for i, draft in enumerate(drafts, start=1)]
    counted = {"passed": 0, "converted": 0, "skipped": 0}
    for a in assets:
        counted[a.gate] += 1

    return Step03VisualOutput(
        location_id=location_id,
        art_style_ref="skills/03-visual/art-style.md",
        assets=assets,
        gate_summary=GateSummary(
            total=len(assets),
            passed=counted["passed"],
            converted=counted["converted"],
            skipped=counted["skipped"],
            note="게이트 판정은 VisualAgent(safety_gate)의 실제 Claude 판단 결과 — 관리자 지정 이미지(assets/{location_id}/{prompt_id}.{ext})가 있으면 그것을 우선 채택하고, 없을 때만 Cloudflare Workers AI(flux-1-schnell)로 자동 생성(status 참고)",
        ),
    )


def build_admin_prompts_md(location_id: str, step02: Step02StoryOutput, step03: Step03VisualOutput) -> str:
    """아직 status가 "ready"가 아닌 자산만 골라, 관리자가 그대로 복사해 외부 AI 도구에
    넣을 수 있는 프롬프트 문서를 만든다. build_chatbot_modal_js()와 같은 자리(dispatch.py)
    에서 호출되어 output/{location_id}/03-image-prompts-for-admin.md로 저장된다."""
    purpose_by_id = {d.prompt_id: d.scene.ko for d in step02.image_prompts_draft}
    pending = [a for a in step03.assets if a.status != "ready"]

    lines = [f"# {location_id} — 관리자용 이미지 생성 프롬프트", ""]
    if not pending:
        lines.append("아직 만들어야 할 이미지가 없습니다 — 전부 준비 완료(ready)됐거나 대상 이미지가 없습니다.")
        return "\n".join(lines) + "\n"

    lines.append(
        "아래 프롬프트를 복사해 외부 AI 이미지/영상 생성 도구에 직접 넣어 만든 뒤, 결과 파일을 "
        "정확히 적힌 저장 경로에 넣어 주세요. 03을 다시 실행하면 자동으로 인식됩니다.\n"
    )
    for a in pending:
        purpose = purpose_by_id.get(a.source_prompt_id, a.caption.ko.replace("[연출]", "").strip())
        lines.append(f"## {a.source_prompt_id}")
        lines.append(f"**용도**: {purpose}")
        if a.final_prompt:
            lines.append(f"**프롬프트**: {a.final_prompt}")
        else:
            lines.append(f"**프롬프트**: (게이트에서 생성 보류됨 — {a.gate_reason})")
        lines.append(f"**저장 경로**: {a.path}")
        lines.append("")

    return "\n".join(lines)
