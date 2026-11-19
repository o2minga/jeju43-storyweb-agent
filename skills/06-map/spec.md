# skills/06-map/spec.md — 06-map 스킬 상세 스펙 ‹현관문›

> 이 문서는 `AGENT-SPEC.md`의 일반 원칙 위에서 06-map만의 세부 규칙을 정의한다.
> **특정 유적지의 실제 좌표·역사 사실은 예시로도 포함하지 않는다.** 아래 값은 전부 플레이스홀더다 — 장소 목록이 바뀌어도 이 문서 내용은 그대로 유지되어야 한다.
> 실행용 요약 지시문은 `SKILL.md`에 있다. 이 문서는 지도 라이브러리 사용·마커·출력 구조의 상세를 담는다.

---

## 0. 아키텍처 위치 (지금 단계)

`AGENT-SPEC.md` 5장 기준 **06-map은 C그룹(조립형)** 이다.

- Claude 호출 없이 **코드 템플릿**으로 입력 데이터를 정적 .html에 끼워 넣는다.
- A그룹(01·02·07·08)이 완료된 뒤, 05 결과가 여러 장소 쌓였을 때 마지막에 돌린다.
- 이 spec의 핵심은 **Leaflet 지도에 위경도 마커를 얹는 방식**과 **장소 확장 구조**다.

---

## 1. 목표

여러 장소의 05 결과를 **Leaflet + OpenStreetMap** 지도 하나에 마커로 얹어 인덱스 첫 화면을 만든다. API 키·도메인 등록이 필요 없고, 장소를 추가하면 마커가 늘어난다.

---

## 2. 입력

`samples/06-map-input-example.json` 형식.

- `places[]` — 각 장소: `location_id`, `name.{ko,en}`, `coord{lat,lng}`, `one_liner.{ko,en}`, `thumbnail`, `page_link`, `timeline_events[]`(선택 — 02-story 산출 그대로)

> 좌표를 위경도 그대로 마커에 쓰므로 지도 이미지 메타(`map` 블록)는 없다.
> `places`가 비면 지도만 렌더링하고 "등록된 장소가 없습니다" 안내만 둔다(마커를 지어내지 않음).

**실제 구현 메모**: 01·02의 JSON에는 좌표가 구조화된 필드로 없고, 카드 원문의 "좌표" 표 행에만 프로즈로 있다. 그래서 `step06_map.extract_coord_from_card()`가 이 스텝(그리고 05가 끝날 때마다)에서 카드 원문을 정규식으로 다시 읽어 `(lat, lng)`를 뽑고, `output/map-places.json` 레지스트리에 장소별로 upsert한다 — 위 `places[]`는 그렇게 만들어진 레지스트리의 논리적 형태이지, 매 실행마다 사람이 미리 채워 넣는 입력이 아니다.

---

## 3. 범위 (포함 / 제외)

**포함**
- Leaflet 지도 + OSM 타일 로딩, 위경도 마커 렌더링, 마커 팝업, 05 링크 연결
- 확대·축소·팬(Leaflet 기본), 여러 장소 자동 맞춤(fitBounds)
- 장소 추가 시 자동 확장

**제외**
- 개별 스토리 페이지(05), 좌표 사실 검증(01·카드)

---

## 4. 지도 구현 규칙 (핵심)

Leaflet 라이브러리가 위경도 ↔ 화면 픽셀 투영(웹 메르카토르)과 줌·팬을 모두 처리한다. 따라서 별도의 좌표→픽셀 변환식이 필요 없다 — 마커에 위경도를 그대로 넘긴다.

**라이브러리 로드** (CDN):

```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

**지도·타일·마커**:

```js
var map = L.map("jeju-map").setView([lat, lng], zoom);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "&copy; OpenStreetMap"
}).addTo(map);

places.forEach(function (p) {
  L.marker([p.lat, p.lng]).addTo(map).bindPopup(popupHtml(p));  // 팝업: 썸네일·이름·한 줄 소개·page_link
});
```

- **마커 위치 고정의 원리**: 마커는 지리 좌표(위경도)에 묶이고 Leaflet이 줌·팬에 맞춰 픽셀 위치를 다시 계산하므로, 확대·축소·이동해도 지도상 같은 지점에 붙어 있다(직접 계산 불필요).
- **초기 화면**: 장소가 1개면 그 위치로 `setView`, 여러 개면 `map.fitBounds(좌표들)`로 모두 보이게 맞춘다. 0개면 제주 중심으로 기본 뷰.
- **로드 타이밍**: 팀 미리보기는 이 문서를 `fetch → document.write` 로 주입하므로, 초기화 스크립트는 `window.L` 가 준비될 때까지 짧게 재시도(polling)한 뒤 지도를 만든다.

---

## 5. 제약

- **Leaflet + OpenStreetMap** 조합 사용. API 키·도메인 등록 없이 동작(타일 로딩에는 인터넷 필요).
- 입력에 없는 장소·좌표를 만들지 않는다.
- 썸네일이 AI 생성물이면 05에서 온 `[연출]` 표시를 유지한다.
- 좌표·정보가 병기(충돌)된 입력은 임의 확정하지 않는다.
- OSM 타일 사용 시 저작자 표시(`&copy; OpenStreetMap`)를 유지한다.

---

## 6. 출력 구조 (정적 .html)

- 단일 `.html`. Leaflet CSS/JS는 CDN에서 로드하고, 장소 데이터는 페이지 안에 `PLACES` 배열로 내장한다.
- 구성: 지도 컨테이너(`#jeju-map`) + 초기화 스크립트(타일 + `PLACES` 순회 마커·팝업) + 빈 상태 안내.
- 확장: `PLACES` 배열을 순회해 마커·팝업을 생성 → 항목 추가만으로 늘어남.

```html
<!-- 개념 골격 (플레이스홀더) -->
<div id="jeju-map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  var PLACES = [ /* {location_id, name, lat, lng, one_liner, thumbnail, page_link}, … */ ];
  // window.L 준비되면: L.map → L.tileLayer(OSM) → PLACES 순회 L.marker+bindPopup → fitBounds
</script>
```

---

## 7. 성공 기준

- [ ] 마커 팝업의 링크 클릭 시 해당 장소의 05 스토리 페이지(`page_link`)로 이동한다
- [ ] 확대·축소·팬이 동작한다 (Leaflet 기본)
- [ ] 마커가 실제 좌표(위경도) 위치에 고정된다
- [ ] `PLACES`에 장소를 추가하면 코드 수정 없이 마커가 늘어난다
- [ ] 장소가 1개여도, 0개여도(안내 문구) 정상 렌더링된다
- [ ] API 키·도메인 등록 없이 동작한다(타일 로딩에는 인터넷 필요)
- [ ] **(중요) 다른 장소 목록으로 실행해도 위 기준을 동일하게 만족한다** — 특정 좌표에 하드코딩되지 않았는지 최종 점검
