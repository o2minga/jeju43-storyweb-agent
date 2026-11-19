"""03-visual(미술감독) 담당 에이전트 — 이미지 생성 전 안전 게이트 강제 + 실제 생성.

generate_asset()은 safety_gate를 통과·변환시킨 최종 프롬프트를 만든 뒤, 다음 순서로
실제 이미지를 확보한다 — **관리자 지정 이미지가 항상 최우선이다(output 캐시보다도
먼저 본다)**. output 캐시를 먼저 보면, 이미 한 번 처리된 장소에 관리자가 나중에
assets/에 새 파일을 넣어도 캐시에 막혀 영영 확인되지 않아 "나중에 바꿔 넣기"라는
기능 목적 자체가 깨지기 때문이다:
1. 프로젝트 루트 assets/{location_id}/{prompt_id}.{ext}(관리자가 외부 AI 도구로 직접
   만들어 넣는 자리)에 파일이 있으면 그것을 output/ 쪽으로 복사해 채택하고,
   Cloudflare는 아예 호출하지 않는다.
2. 없으면 output/{location_id}/assets/{prompt_id}.{ext}에 파일이 이미 있는지 본다 —
   있으면 그대로 재사용("ready", 재생성 비용 절약용).
3. 그래도 없으면 Cloudflare Workers AI(flux-1-schnell, generate.image_backend)로 실제
   생성을 시도한다. CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN이 없거나 호출이
   실패하면 조용히 4번으로 넘어간다(파이프라인을 막지 않는다).
4. 그래도 없으면 "awaiting_manual_generation" — 03-image-prompts-for-admin.md에 이
   프롬프트가 실려 관리자가 채워 넣을 수 있게 한다. 관리자가 1번 자리에 파일을 넣고 나면
   다음 실행에서 자동으로 "ready"로 바뀐다.

다른 Group A 에이전트(VerifyAgent 등)와 달리 Agent 기반 클래스를 상속하지 않는다 —
Agent.run()은 "system_prompt + user_input을 한 번의 LLM 호출로 output_schema 하나에
채워 넣는" 형태를 가정하는데, VisualAgent는 02가 넘긴 이미지 프롬프트 각각에 대해
"게이트 판단 → (통과/변환된 프롬프트로) 실제 생성/재사용/폴백"을 반복하는 제어 흐름이라
그 형태에 맞지 않는다.

핵심 안전장치: generate_asset()이 이 클래스가 노출하는 유일한 진입점이고, 그 내부에서
safety_gate()를 무조건 먼저 호출한 뒤에만 _generate_or_locate()에 도달한다.
_generate_or_locate()는 이 모듈 밖에서 import되지 않고 generate_asset() 안에서만
호출되므로, safety_gate를 건너뛰고 곧장 생성/저장 자리 확인으로 가는 코드 경로 자체가
없다 — VerifyAgent의 bounded_search처럼 "모델이 tool_choice=auto로 스스로 호출 여부를
판단"하게 맡기지 않은 것도 같은 이유다: 이 게이트는 모델의 재량이 아니라 코드가
항상 강제해야 하는 필수 단계이기 때문이다. tools에는 그래도 safety_gate를 등록해
두어, 다른 도구들과 동일한 형태로 존재를 드러내고 필요하면 대화형으로도 참조할 수
있게 한다.
"""
from __future__ import annotations

import logging
from pathlib import Path

from generate import image_backend
from generate.common import OUTPUT_ROOT, location_asset_path
from subagents.safety_gate import safety_gate

logger = logging.getLogger("agent.agents.visual_agent")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_ROOT = REPO_ROOT / "assets"  # 관리자가 외부 도구로 만든 파일을 직접 넣는 레거시 자리
_ART_STYLE_PATH = REPO_ROOT / "skills" / "03-visual" / "art-style.md"

_SAFETY_GATE_TOOL = {
    "name": "safety_gate",
    "description": (
        "이미지를 실제로 생성하기 전에 반드시 통과시켜야 하는 재현 금지 게이트. 잔인한 "
        "피해 장면의 직접 묘사, 실존 인물(피해자·생존자·가해자)의 얼굴 재현, 폭력 행위가 "
        "실행되는 순간의 사실적 재현을 차단하고 상징적 대체 표현을 제안한다."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_prompt": {"type": "string", "description": "검사할 이미지 생성 프롬프트"},
        },
        "required": ["image_prompt"],
    },
    "handler": safety_gate,
}


def _load_art_style() -> tuple[str, str]:
    """art-style.md에서 (한국어 톤 요약, 프롬프트 끝에 첨부할 영문 스니펫)을 읽어온다.
    파일이 없으면 둘 다 빈 문자열 — style_notes/스타일 첨부를 그냥 생략한다."""
    if not _ART_STYLE_PATH.exists():
        return "", ""
    text = _ART_STYLE_PATH.read_text(encoding="utf-8")

    summary = ""
    marker = "## 0. 대전제 (톤의 뿌리)"
    if marker in text:
        after = text.split(marker, 1)[1]
        summary = after.split("\n## ", 1)[0].strip()

    snippet = ""
    fence_parts = text.split("```")
    if len(fence_parts) >= 3:
        snippet = fence_parts[-2].strip()

    return summary, snippet


class VisualAgent:
    """name/tools만 다른 에이전트와 형태를 맞추고, 실제 실행은 generate_asset()으로 한다."""

    name = "visual"

    def __init__(self):
        self.tools: list[dict] = [_SAFETY_GATE_TOOL]

    def generate_asset(self, prompt_id: str, location_id: str, image_prompt: str, ext: str = "png") -> dict:
        """image_prompt 하나를 처리한다 — safety_gate()를 항상 먼저 거친다.

        반환값: {"gate": "passed"|"converted"|"skipped", "gate_reason": str,
        "record": dict|None}. record는 {"prompt_id","final_prompt","target_path","status",
        "generated_by",("style_notes")} — generated_by는 "cloudflare-workers-ai"|
        "existing-file"|"manual-legacy-copy"|None(아직 준비 안 됨)로, step03_visual.py가
        이를 보고 source 문구를 정한다. gate="skipped"(상징적 대체안도 없어 만들 프롬프트
        자체가 없는 경우)일 때만 record 자체가 None이다.
        """
        verdict = safety_gate(image_prompt)

        if verdict["passed"]:
            gate, gate_reason, prompt_to_render = "passed", verdict["reason"], image_prompt
        elif verdict["suggested_alternative"]:
            gate, gate_reason, prompt_to_render = "converted", verdict["reason"], verdict["suggested_alternative"]
        else:
            gate, gate_reason, prompt_to_render = "skipped", verdict["reason"], None

        record = (
            self._generate_or_locate(prompt_id, location_id, prompt_to_render, ext)
            if prompt_to_render
            else None
        )
        return {"gate": gate, "gate_reason": gate_reason, "record": record}

    @staticmethod
    def _generate_or_locate(prompt_id: str, location_id: str, prompt_to_render: str, ext: str) -> dict:
        """최종 프롬프트·저장 경로를 정하고, 위 클래스 docstring의 1→4 순서로 실제
        파일을 확보한다. generate_asset()을 통해서만(=safety_gate를 먼저 거친 뒤에만)
        호출된다."""
        style_summary, style_snippet = _load_art_style()
        final_prompt = f"{prompt_to_render} — {style_snippet}" if style_snippet else prompt_to_render

        target_path = location_asset_path(location_id, "assets", f"{prompt_id}.{ext}")
        target_abs = OUTPUT_ROOT / location_id / "assets" / f"{prompt_id}.{ext}"

        record = {
            "prompt_id": prompt_id,
            "final_prompt": final_prompt,
            "target_path": target_path,
            "status": "awaiting_manual_generation",
            "generated_by": None,
        }
        if style_summary:
            record["style_notes"] = style_summary

        # 관리자 지정 이미지 우선 확인 — output 캐시보다도 먼저 본다. output 캐시를
        # 먼저 보면, 이미 한 번 처리된 장소에 관리자가 나중에 assets/에 새 파일을
        # 넣어도 캐시에 막혀 영영 확인되지 않는다 — "관리자가 나중에 바꿔 넣을 수
        # 있게 한다"는 이 기능의 목적 자체가 깨진다. 그래서 관리자 지정 파일은 항상
        # 최우선으로 확인하고, output 캐시는 "관리자 지정이 없을 때"의 재생성 비용
        # 절약 수단으로만 둔다.
        legacy_path = ASSETS_ROOT / location_id / f"{prompt_id}.{ext}"
        if legacy_path.exists():
            logger.info(
                "관리자 지정 이미지 우선 확인: %s에 파일이 있어 Cloudflare 호출 없이 그대로 사용합니다.",
                legacy_path,
            )
            target_abs.parent.mkdir(parents=True, exist_ok=True)
            target_abs.write_bytes(legacy_path.read_bytes())
            record["status"] = "ready"
            record["generated_by"] = "manual-legacy-copy"
            return record

        if target_abs.exists():
            record["status"] = "ready"
            record["generated_by"] = "existing-file"
            return record

        image_bytes = image_backend.try_generate(final_prompt)
        if image_bytes is not None:
            target_abs.parent.mkdir(parents=True, exist_ok=True)
            target_abs.write_bytes(image_bytes)
            record["status"] = "ready"
            record["generated_by"] = "cloudflare-workers-ai"
            return record

        return record
