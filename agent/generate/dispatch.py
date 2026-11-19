"""step_id -> 실제 생성 함수 매핑. run_agent.py는 이 모듈의 generate_step()만 안다.

run_agent.py 쪽 결과 딕셔너리(results)의 규칙: JSON 스텝(01,02,03,04,07,08)은 검증된
pydantic 모델 인스턴스를, HTML 스텝(05,06)은 원문 HTML 문자열을 값으로 담는다. 이
모듈의 각 스텝 생성 함수는 그 규칙에 맞춰 results에서 이전 스텝 결과를 읽는다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import (
    step01_verify,
    step02_story,
    step03_visual,
    step04_audio,
    step05_assemble,
    step06_map,
    step07_chatbot,
    step08_review,
)
from .common import OUTPUT_ROOT, write_json, write_text


def _loc_dir(location_id: str) -> Path:
    return OUTPUT_ROOT / location_id


def _compute_map_html(location_id: str, card_text: str | None, results: dict[str, Any]) -> str:
    """06-map 로직(좌표 추출 → registry upsert → 렌더링)을 계산한다.

    "06" 스텝 자체와, "05" 스텝이 끝날 때마다 최신 지도를 Supabase에 같이 올리기 위한
    호출 양쪽에서 공유한다 — 두 번 호출돼도 registry upsert는 멱등이라 안전하다.
    """
    coord = step06_map.extract_coord_from_card(card_text) if card_text else None
    step02 = results["02"]
    step03 = results.get("03")

    thumbnail = ""
    if step03 is not None and step03.assets:
        asset_path = step03.assets[0].path  # "output/{location_id}/assets/xxx.png"
        prefix = f"output/{location_id}/"
        thumbnail = f"{location_id}/{asset_path[len(prefix):]}" if asset_path.startswith(prefix) else asset_path

    page_link = f"{location_id}/05-assemble.html"

    if coord is not None:
        places = step06_map.upsert_place(
            location_id,
            step02.location_name.ko or location_id,
            coord,
            step02.story.intro.ko,
            thumbnail,
            page_link,
        )
    else:
        places = step06_map.load_registry()

    return step06_map.generate(places)


def generate_step(
    step_id: str,
    location_id: str,
    card_text: str | None,
    results: dict[str, Any],
    extra_instruction: str | None = None,
):
    """이 스텝의 출력을 생성해 디스크에 쓰고 (path, raw_data)를 반환한다.

    raw_data는 JSON 스텝이면 dict, HTML 스텝이면 str이다 — run_agent.py가 그대로
    schema.validate.validate_step()에 넘길 수 있는 형태다.

    extra_instruction: agent/subagents/self_repair.py가 08 검수 fail 항목을 "전체를
    다시 만들지 말고 이 부분만 좁게 고쳐 달라"고 재요청할 때만 채워지는 추가 지시다.
    01/02/07(Claude 호출 스텝)에서만 실제로 쓰이고, 나머지 결정론적 스텝은 무시한다
    (05는 애초에 Claude를 호출하지 않으므로 재요청도 "그대로 다시 조립" 이상은 못 한다).
    평소 실행(run_agent.py가 --repair 없이 호출)에서는 항상 None이라 기존 동작과 완전히
    동일하다.
    """
    if step_id == "01":
        model = step01_verify.generate(card_text, extra_instruction=extra_instruction)
        path = _loc_dir(location_id) / "01-verify.json"
        data = model.model_dump(mode="json")
        write_json(path, data)
        return path, data

    if step_id == "02":
        model = step02_story.generate(card_text, results["01"], extra_instruction=extra_instruction)
        path = _loc_dir(location_id) / "02-story.json"
        data = model.model_dump(mode="json")
        write_json(path, data)
        return path, data

    if step_id == "03":
        model = step03_visual.generate(location_id, results["02"])
        path = _loc_dir(location_id) / "03-visual.json"
        data = model.model_dump(mode="json")
        write_json(path, data)

        admin_md = step03_visual.build_admin_prompts_md(location_id, results["02"], model)
        write_text(_loc_dir(location_id) / "03-image-prompts-for-admin.md", admin_md)

        return path, data

    if step_id == "04":
        model = step04_audio.generate(location_id, results["02"])
        path = _loc_dir(location_id) / "04-audio.json"
        data = model.model_dump(mode="json")
        write_json(path, data)
        return path, data

    if step_id == "07":
        model = step07_chatbot.generate(location_id, results["01"], results["02"], extra_instruction=extra_instruction)
        path = _loc_dir(location_id) / "07-chatbot.json"
        data = model.model_dump(mode="json")
        write_json(path, data)

        location_name_ko = results["02"].location_name.ko or location_id
        js_text = step07_chatbot.build_chatbot_modal_js(location_name_ko, model, results["02"].chatbot_kb)
        write_text(_loc_dir(location_id) / "chatbot-modal.js", js_text)
        return path, data

    if step_id == "05":
        html = step05_assemble.generate(
            location_id,
            results["01"],
            results["02"],
            results.get("03"),
            results.get("04"),
            chatbot_modal_relpath="chatbot-modal.js",
        )
        path = _loc_dir(location_id) / "05-assemble.html"
        write_text(path, html)

        # Supabase 동기화는 여기서 하지 않는다 — agent/hooks/supabase_sync.py가
        # after_step("05") 시점에 전담한다(05를 재사용한 경우도 매번 동기화하도록
        # 일원화, 이 함수가 새로 생성됐을 때만 도는 것과는 트리거 조건이 다르다).
        #
        # 다만 _compute_map_html() 호출 자체는 그대로 남긴다 — 반환된 html은 이제 안
        # 쓰지만, 그 안의 step06_map.upsert_place()가 이 장소의 좌표·썸네일을
        # 레지스트리(map-places.json)에 등록/갱신하는 부수효과가 필요하다. 06 스텝은
        # output/index.html이 이미 있으면(다른 장소를 먼저 처리해서) 다시 실행되지
        # 않으므로, 이 등록이 05에서라도 일어나지 않으면 새 장소가 지도에서 누락된다.
        _compute_map_html(location_id, card_text, results)

        return path, html

    if step_id == "06":
        html = _compute_map_html(location_id, card_text, results)
        path = OUTPUT_ROOT / "index.html"
        write_text(path, html)
        return path, html

    if step_id == "08":
        model = step08_review.generate(
            location_id,
            results.get("01"),
            results.get("02"),
            results.get("03"),
            results.get("04"),
            results.get("05"),
            results.get("06"),
            results.get("07"),
        )
        path = _loc_dir(location_id) / "review_result.json"
        data = model.model_dump(mode="json")
        write_json(path, data)

        if results.get("02") is not None and results.get("01") is not None and results.get("05") is not None:
            location_name_ko = results["02"].location_name.ko or location_id
            ledger_md = step08_review.build_source_ledger_md(
                location_name_ko, results["01"], results.get("03"), results["05"]
            )
            write_text(_loc_dir(location_id) / "source-ledger.md", ledger_md)

            summary_md = step08_review.build_review_summary_md(location_name_ko, model)
            write_text(_loc_dir(location_id) / "review-summary.md", summary_md)

        return path, data

    raise ValueError(f"알 수 없는 step_id: {step_id!r}")
