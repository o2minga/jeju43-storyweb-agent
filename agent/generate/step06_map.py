"""06-map 실제 생성 — Group C(조립형): Claude를 호출하지 않고, 05까지 끝난 장소들을
Leaflet + OpenStreetMap 지도 위 마커로 조립한다. 좌표(위경도)를 그대로 마커에 찍으므로
좌표→픽셀 변환·베이스 지도 이미지가 필요 없다(spec.md 4장 참조).

여러 장소를 계속 쌓아 나가야 하므로(카드가 늘어날 때마다 마커가 늘어남), 장소 목록을
output/map-places.json 레지스트리에 upsert 방식으로 유지한다. 좌표는 01/02의 JSON에는
구조화된 필드로 없고 카드 원문의 "좌표" 표 행에만 프로즈로 있으므로, 이 레지스트리를
채울 때만 예외적으로 카드 원문을 정규식으로 다시 읽는다(01/02 체인을 건드리지 않음).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import OUTPUT_ROOT

REGISTRY_PATH = OUTPUT_ROOT / "map-places.json"

# 디자인을 별도 파일로 분리(spec.md 4장) — 이 파일 교체만으로 톤 변경 가능.
_DESIGN_CSS_PATH = Path(__file__).resolve().parent.parent.parent / "skills" / "06-map" / "css" / "index.css"

# Leaflet CDN(핀 불필요, 오픈소스). 지도 타일은 OpenStreetMap.
LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
# 장소가 없을 때 지도 초기 중심(제주도 대략 중앙)·줌
JEJU_CENTER = (33.38, 126.53)
JEJU_ZOOM = 10

_COORD_RE = re.compile(r"\|\s*좌표\s*\|\s*([\d.]+)\s*,\s*([\d.]+)")
# 묶음 카드(여러 지점을 표로 나열한 카드, 예: 너븐숭이와 북촌 유적군)는 좌표가
# "| 좌표 | lat, lng |" 한 줄이 아니라 "| 지점 | 주소 | 좌표 | 성격 |" 같은 여러 지점
# 표로 나온다 — 이때는 대표 지점으로 표시된 "(본체)" 행에서 좌표를 뽑는다.
_COORD_PAIR_RE = re.compile(r"([\d]{2,3}\.[\d]+)\s*,\s*([\d]{2,3}\.[\d]+)")


def extract_coord_from_card(card_text: str) -> tuple[float, float] | None:
    """카드 원문에서 이 장소를 대표하는 (lat, lng)를 뽑는다.

    1. 단일 좌표 카드: '| 좌표 | lat, lng ... |' 표 행.
    2. 묶음 카드: '(본체)'로 표시된 대표 지점이 있는 행에서 좌표를 뽑는다.
    둘 다 없으면 None.
    """
    m = _COORD_RE.search(card_text)
    if m:
        return float(m.group(1)), float(m.group(2))

    for line in card_text.splitlines():
        if "(본체)" in line:
            m2 = _COORD_PAIR_RE.search(line)
            if m2:
                return float(m2.group(1)), float(m2.group(2))

    return None


def _one_liner_from_intro(intro_ko: str) -> str:
    for sep in ("? ", "?", ". ", ".", "\n"):
        if sep in intro_ko:
            return intro_ko.split(sep)[0].strip()
    return intro_ko[:60].strip()


def load_registry() -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(places: list[dict]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(places, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_place(
    location_id: str,
    name_ko: str,
    coord: tuple[float, float],
    intro_ko: str,
    thumbnail: str,
    page_link: str,
) -> list[dict]:
    """레지스트리에 이 장소를 추가/갱신하고, 갱신된 전체 목록을 반환한다.

    기존 항목을 통째로 새 dict로 교체하지 않고 병합한다 — 이 함수가 관리하는
    필드(name.ko/coord/one_liner.ko/thumbnail/page_link)만 갱신하고, 이 함수가
    모르는 필드(예: name.en·one_liner.en·timeline_events처럼 다른 스텝·수작업으로
    채워진 값)는 그대로 보존한다. 그렇지 않으면 카드를 다시 처리할 때마다 이런
    값들이 조용히 사라진다.
    """
    places = load_registry()
    existing = next((p for p in places if p["location_id"] == location_id), None)
    entry = dict(existing) if existing else {}

    entry["location_id"] = location_id
    entry["name"] = {**entry.get("name", {}), "ko": name_ko}
    entry["name"].setdefault("en", "")
    entry["coord"] = {"lat": coord[0], "lng": coord[1]}
    entry["one_liner"] = {**entry.get("one_liner", {}), "ko": _one_liner_from_intro(intro_ko)}
    entry["one_liner"].setdefault("en", "")
    entry["thumbnail"] = thumbnail
    entry["page_link"] = page_link

    places = [p for p in places if p["location_id"] != location_id]
    places.append(entry)
    save_registry(places)
    return places


def _places_for_client(places: list[dict]) -> list[dict]:
    """클라이언트 JS(PLACES 배열)에 넘길 최소 필드만 추린다."""
    return [
        {
            "location_id": p["location_id"],
            "name": p["name"]["ko"],
            "lat": p["coord"]["lat"],
            "lng": p["coord"]["lng"],
            "one_liner": p["one_liner"]["ko"],
            "thumbnail": p["thumbnail"],
            "page_link": p["page_link"],
        }
        for p in places
    ]


def generate(places: list[dict]) -> str:
    # 마커는 위경도로 직접 찍으므로 좌표→픽셀 변환·베이스 이미지가 필요 없다.
    places_json = json.dumps(_places_for_client(places), ensure_ascii=False)
    center_lat, center_lng = JEJU_CENTER
    css_text = _DESIGN_CSS_PATH.read_text(encoding="utf-8")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>제주 4·3 유적지 지도 — 인덱스</title>
<link rel="stylesheet" href="{LEAFLET_CSS}"/>
<style>
{css_text}
</style>
</head>
<body>

<div id="toolbar">
  <button id="fzMinus" title="글자 작게" aria-label="글자 작게">A-</button>
  <button id="fzPlus" title="글자 크게" aria-label="글자 크게">A+</button>
</div>

<section class="hero">
  <span class="badge">제주 4·3 유적지 스토리 지도</span>
  <h1>지도 위에서 만나는<br>제주 4·3의 자리들</h1>
  <p class="lead">지도의 핀이나 아래 목록의 장소를 눌러 각 장소에 담긴 이야기로 이동하세요. 검증된 사실을 바탕으로 만든 이야기·이미지·오디오·챗봇을 함께 만나볼 수 있습니다.</p>
  <p class="scroll-hint">아래로 스크롤해 둘러보기 ↓</p>
</section>

<section class="explore">
  <div class="wrap">
    <p class="kicker">EXPLORE</p>
    <h2 class="section-title">유적지 둘러보기</h2>
    <div class="explore-grid">
      <div id="jeju-map"></div>
      <div class="card-list" id="cardList"></div>
    </div>
    <p class="map-note" style="color:var(--text-sub);font-size:0.78em;margin-top:8px;">지도 데이터 © OpenStreetMap 기여자 · 지도 표시 라이브러리: Leaflet</p>
  </div>
</section>

<section class="detail">
  <div class="wrap">
    <p class="kicker">DETAIL</p>
    <h2 class="section-title">선택한 장소</h2>
    <div class="detail-card" id="detailCard">
      <div class="detail-empty">
        <span>장소를 선택하면 소개가 여기에 표시됩니다.</span>
      </div>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <h3>출처와 고지</h3>
    <ul class="src-list" id="srcList"></ul>
    <div class="badge-legend">
      <span><span class="fx-tag">연출</span> 실제 기록이 아닌 AI 연출 이미지·영상</span>
      <span><span class="ai-tag">AI 생성</span> AI가 생성한 이미지·음성·영상</span>
    </div>
    <p class="warn">제주 4·3은 민감한 역사 소재입니다 — 각 장소 페이지 하단의 출처 대장에서 근거를 확인하세요.</p>
  </div>
</footer>

<script src="{LEAFLET_JS}"></script>
<script>
(function () {{
  "use strict";
  var PLACES = {places_json};

  // 글자크기 툴바 — html{{font-size:calc(var(--fz-base)*var(--fz,1))}} 토큰을 그대로 이용.
  var FZ_MIN = 0.9, FZ_MAX = 1.3, FZ_STEP = 0.1;
  var fz = 1;
  function applyFz() {{ document.documentElement.style.setProperty("--fz", fz.toFixed(2)); }}
  document.getElementById("fzMinus").addEventListener("click", function () {{
    fz = Math.max(FZ_MIN, +(fz - FZ_STEP).toFixed(2)); applyFz();
  }});
  document.getElementById("fzPlus").addEventListener("click", function () {{
    fz = Math.min(FZ_MAX, +(fz + FZ_STEP).toFixed(2)); applyFz();
  }});

  var cardList = document.getElementById("cardList");
  var srcList = document.getElementById("srcList");

  if (!PLACES.length) {{
    cardList.insertAdjacentHTML("beforeend", '<p class="empty-note">등록된 장소가 없습니다.</p>');
    srcList.insertAdjacentHTML("beforeend", "<li>등록된 장소가 없습니다.</li>");
  }}

  function selectPlace(locationId) {{
    var p = PLACES.filter(function (x) {{ return x.location_id === locationId; }})[0];
    if (!p) return;

    Array.prototype.forEach.call(cardList.querySelectorAll(".place-card"), function (el) {{
      el.classList.toggle("active", el.dataset.locationId === locationId);
    }});

    var detailCard = document.getElementById("detailCard");
    detailCard.innerHTML =
      (p.thumbnail ? '<div class="thumb-wrap" style="max-width:360px;margin-bottom:16px;"><span class="fx-tag">연출</span><img src="' + p.thumbnail + '" alt="" style="width:100%;border-radius:8px;display:block;"></div>' : "") +
      "<h3>" + p.name + "</h3>" +
      (p.one_liner ? "<p>" + p.one_liner + "</p>" : "") +
      '<a class="btn-link" href="' + p.page_link + '">자세히 보기</a>';
  }}

  PLACES.forEach(function (p) {{
    var card = document.createElement("div");
    card.className = "place-card";
    card.dataset.locationId = p.location_id;
    card.innerHTML =
      (p.thumbnail ? '<div class="thumb-wrap" style="margin-bottom:8px;"><span class="fx-tag">연출</span><img src="' + p.thumbnail + '" alt="" style="width:100%;border-radius:6px;display:block;"></div>' : "") +
      '<div style="font-weight:700;">' + p.name + "</div>" +
      (p.one_liner ? '<div style="font-size:0.9em;color:var(--text-sub);margin-top:4px;">' + p.one_liner + "</div>" : "");
    card.addEventListener("click", function () {{ selectPlace(p.location_id); }});
    cardList.appendChild(card);

    var li = document.createElement("li");
    li.innerHTML = '<b>' + p.name + '</b> — 자세한 출처는 <a href="' + p.page_link + '" style="color:#fff;">해당 장소 페이지</a> 하단 출처 대장을 참고하세요.';
    srcList.appendChild(li);
  }});

  // Leaflet(외부 CDN)이 아직 로드되지 않았으면 잠시 뒤 다시 시도한다.
  // (팀 미리보기는 fetch→document.write 로 이 문서를 주입하므로 로드 타이밍이 유동적이다)
  function init() {{
    if (!window.L) {{ return setTimeout(init, 50); }}

    var map = L.map("jeju-map", {{ zoomControl: false }}).setView([{center_lat}, {center_lng}], {JEJU_ZOOM});
    L.control.zoom({{ position: "topleft" }}).addTo(map);
    // CartoDB Positron — 차분한 회색조 베이스맵(지형색 배제, 육지는 흰색/밝은 회색)이라
    // 아래 커스텀 서클 마커(빨강)가 상대적으로 도드라져 보인다.
    L.tileLayer("https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
      maxZoom: 20,
      subdomains: "abcd",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a> | <a href="https://leafletjs.com/" target="_blank" rel="noopener">Leaflet</a>'
    }}).addTo(map);

    var MARKER_COLOR = "#d90429"; // CSS --accent-color 와 동일 — 회색조 지도 위에서 눈에 띄게
    var bounds = [];
    PLACES.forEach(function (p) {{
      var marker = L.circleMarker([p.lat, p.lng], {{
        radius: 9,
        weight: 2,
        color: "#ffffff",
        fillColor: MARKER_COLOR,
        fillOpacity: 1
      }}).addTo(map);
      var html = "";
      if (p.thumbnail) html += '<div class="thumb-wrap"><span class="fx-tag">연출</span><img src="' + p.thumbnail + '" alt=""></div>';
      html += '<div><a href="' + p.page_link + '">' + p.name + "</a></div>";
      if (p.one_liner) html += '<div>' + p.one_liner + "</div>";
      marker.bindPopup(html, {{ maxWidth: 220 }});
      marker.on("click", function () {{ selectPlace(p.location_id); }});
      bounds.push([p.lat, p.lng]);
    }});

    if (bounds.length === 1) {{ map.setView(bounds[0], 12); }}
    else if (bounds.length > 1) {{ map.fitBounds(bounds, {{ padding: [40, 40] }}); }}
  }}
  init();
}})();
</script>
</body>
</html>
"""
