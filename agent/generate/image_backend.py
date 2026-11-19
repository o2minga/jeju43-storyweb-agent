"""Cloudflare Workers AI(flux-1-schnell) 이미지 생성 백엔드.

CLOUDFLARE_ACCOUNT_ID·CLOUDFLARE_API_TOKEN이 없거나 호출이 실패하면 None을 반환한다 —
호출부(agents/visual_agent.py)가 그 경우 관리자 수동 생성(assets/{location_id}/{prompt_id}.{ext})
으로 폴백한다. 재현 금지 게이트를 통과한 최종 프롬프트만 여기 도달하므로, 이 모듈 자체는
안전성 판단을 하지 않는다.
"""
from __future__ import annotations

import base64
import io
import logging
import os

import httpx
from PIL import Image

logger = logging.getLogger("agent.generate.image_backend")

_MODEL = "@cf/black-forest-labs/flux-1-schnell"
_TIMEOUT = 60.0


def try_generate(prompt: str) -> bytes | None:
    """prompt로 이미지를 실제 생성해 PNG 바이트를 반환한다. 미설정/실패 시 None.

    flux-1-schnell 응답이 실제로는 JPEG일 때가 있어(관측됨), 저장 확장자(.png)와
    실제 포맷이 어긋나지 않도록 항상 PNG로 정규화해서 반환한다.
    """
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token:
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{_MODEL}"
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_token}"},
            json={"prompt": prompt},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        image_b64 = data["result"]["image"]
        raw_bytes = base64.b64decode(image_b64)

        with Image.open(io.BytesIO(raw_bytes)) as img:
            out = io.BytesIO()
            img.convert("RGB").save(out, format="PNG")
            return out.getvalue()
    except Exception as exc:  # noqa: BLE001 - 실패는 관리자 수동 생성 폴백 신호일 뿐, 파이프라인을 죽이지 않는다
        logger.warning("Cloudflare Workers AI 이미지 생성 실패 — 관리자 수동 생성으로 폴백: %s", exc)
        return None
