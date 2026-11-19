"""06-map 출력 검증 — skills/06-map/spec.md 6장(출력 구조)·7장(성공 기준) 반영.

06은 Leaflet + OpenStreetMap 지도 위에 마커를 얹는다. 산출물이 .html이라, 지도 컨테이너
(#jeju-map)·Leaflet 로드·마커 데이터(PLACES: location_id/좌표/page_link)·빈 상태 안내
문구가 실제로 존재하는지 파싱해 Pydantic으로 검증한다. (마커는 클라이언트 JS가 PLACES
배열로 생성하므로 DOM이 아니라 그 데이터 배열을 검증한다.)
"""
from __future__ import annotations

import json
import re
from typing import List

from bs4 import BeautifulSoup
from pydantic import model_validator

from .common import StrictModel

_PLACES_RE = re.compile(r"var\s+PLACES\s*=\s*(\[.*?\]);", re.DOTALL)
_EMPTY_MSG = "등록된 장소가 없습니다"


class Marker(StrictModel):
    location_id: str
    href: str  # page_link
    lat: float
    lng: float


class Step06MapOutput(StrictModel):
    map_container_present: bool
    leaflet_present: bool
    markers: List[Marker]
    empty_state_message_present: bool

    @model_validator(mode="after")
    def _check_rules(self):
        if not self.map_container_present:
            raise ValueError("지도 컨테이너(#jeju-map)가 없습니다.")
        if not self.leaflet_present:
            raise ValueError("Leaflet(지도 라이브러리) 로드가 없습니다.")
        if not self.markers and not self.empty_state_message_present:
            raise ValueError(
                "장소(places)가 0개인데 '등록된 장소가 없습니다' 안내 문구가 없습니다 "
                "(마커를 지어내면 안 되지만, 안내 문구는 반드시 있어야 함)."
            )
        for m in self.markers:
            if not m.href:
                raise ValueError(f"마커(location_id={m.location_id!r})에 page_link(href)가 없습니다.")
        return self


def parse_map_html(html: str) -> Step06MapOutput:
    soup = BeautifulSoup(html, "html.parser")

    map_container = soup.select_one("#jeju-map")
    leaflet_present = "leaflet" in html.lower()

    markers: List[Marker] = []
    m = _PLACES_RE.search(html)
    if m:
        for p in json.loads(m.group(1)):
            markers.append(
                Marker(
                    location_id=p.get("location_id", ""),
                    href=p.get("page_link", ""),
                    lat=p["lat"],
                    lng=p["lng"],
                )
            )

    empty_present = _EMPTY_MSG in html  # 빈 상태 안내는 JS 문자열 리터럴로 항상 포함

    return Step06MapOutput(
        map_container_present=map_container is not None,
        leaflet_present=leaflet_present,
        markers=markers,
        empty_state_message_present=empty_present,
    )
