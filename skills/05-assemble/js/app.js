/* ============================================================
   제주 4·3 스토리웹 — app.js  (index.html 인덱스 페이지용)
   1) data/sites.json 위도/경도 → 지도 마커 생성
   2) 마커/카드 클릭 → 상세(스토리) 뷰로 자연스러운 전환(스크롤+강조)
   3) 생소한 역사 용어 hover/focus/tap → 팝업 툴팁 풀이
   의존: Leaflet(전역 L), CSS 변수(design.md)
   ============================================================ */
'use strict';

/* ========== 0. 설정 ========== */
const CONFIG = {
  dataUrl: 'data/sites.json',
  jejuCenter: [33.38, 126.55],
  jejuZoom: 10,
  focusZoom: 13,
};

/* 역사 용어 사전/툴팁 = js/glossary.js (window.Glossary), 스크롤 등장 = js/reveal.js (window.Reveal) */

/* ========== 2. 전역 상태 ========== */
let SITES = [];
let map = null;
const markers = {};
let activeId = null;
let activeRegion = '전체';

/* ========== 3. 진입점 ========== */
document.addEventListener('DOMContentLoaded', init);

async function init() {
  initToolbar();
  if (window.I18n) window.I18n.init();                  // 언어 토글 초기화 (다른 렌더보다 먼저)
  Reveal.init();
  Glossary.init();
  Glossary.apply(document.querySelector('.hero'));      // 히어로 텍스트에 용어 툴팁

  try {
    const res = await fetch(CONFIG.dataUrl);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    SITES = (await res.json()).sites || [];
  } catch (err) {
    console.error('[sites.json 로드 실패]', err);
    showMapFallback();
    return;
  }

  buildFilters();
  initMap();
  renderMarkers();
  renderCards();

  // 언어 변경 시 데이터 기반 화면 재렌더
  if (window.I18n) window.I18n.onChange(onLangChange);

  // 챗봇 등에서 넘어온 딥링크(#site=id) → 해당 장소 자동 선택
  const m = /#site=([^&]+)/.exec(location.hash);
  if (m) selectSite(decodeURIComponent(m[1]), { pan: true });
}

/* i18n 편의: 데이터 필드/문구 선택 */
function fld(obj, field) { return window.I18n ? window.I18n.pick(obj, field) : (obj[field] || ''); }
function T(key, vars) { return window.I18n ? window.I18n.t(key, vars) : key; }
function kindLabel(kind) { return T('kind.' + kind); }
function regionLabel(region) {
  const s = SITES.find((x) => x.region === region);
  return s ? fld(s, 'region') : region;
}

/* 언어 변경 → 필터·카드·마커팝업·상세 다시 그림 */
function onLangChange() {
  if (!SITES.length) return;
  buildFilters();
  renderCards();
  Object.keys(markers).forEach((id) => {
    const s = SITES.find((x) => x.id === id);
    if (s && markers[id].getPopup) markers[id].setPopupContent(popupHtml(s));
  });
  if (activeId) { const s = SITES.find((x) => x.id === activeId); if (s) renderDetail(s); }
}

/* ========== 4. 툴바 (글자 크기) ========== */
function initToolbar() {
  // 인라인 onclick 대신 이벤트 위임 (HTML의 onclick="fz(..)"도 계속 호환되게 전역 노출)
  window.fz = fz;
}
function fz(d) {
  const el = document.documentElement;
  let v = d === 0 ? 1 : parseFloat(el.style.getPropertyValue('--fz') || 1) + d * 0.08;
  v = Math.max(0.85, Math.min(1.4, v));
  el.style.setProperty('--fz', v.toFixed(2));
}

/* ========== 6. 권역 필터 ========== */
function buildFilters() {
  const regions = ['전체', ...new Set(SITES.map((s) => s.region))];   // '전체'=센티넬, 나머지는 ko 원문(필터 기준)
  const box = document.getElementById('filters');
  box.innerHTML = '';
  regions.forEach((r) => {
    const b = document.createElement('button');
    b.className = 'chip' + (r === activeRegion ? ' active' : '');
    b.textContent = r === '전체' ? T('filter.all') : regionLabel(r);
    b.setAttribute('aria-pressed', String(r === activeRegion));
    b.onclick = () => { activeRegion = r; buildFilters(); renderCards(); fitToRegion(); };
    box.appendChild(b);
  });
}

/* ========== 7. 지도 ========== */
function initMap() {
  // 지도 위에서 휠 스크롤 → 확대/축소 (휠 업=확대, 휠 다운=축소)
  map = L.map('map', { scrollWheelZoom: true }).setView(CONFIG.jejuCenter, CONFIG.jejuZoom);
  // 다크 테마에 맞춘 CARTO dark 베이스맵
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap &copy; CARTO',
  }).addTo(map);
}

/* 위도/경도 → 마커: 대표=큰 원, 연계/부속=작은 원, area(한모살)=면(circle) */
function renderMarkers() {
  const sea = cssVar('--sea');
  const accent = cssVar('--accent');

  SITES.forEach((s) => {
    if (typeof s.lat !== 'number' || typeof s.lng !== 'number') return;
    const isRep = s.kind === '대표';
    let m;

    if (s.shape === 'area') {
      // 특정 지점이 아닌 '면'으로 표현 (카드 비고 지침)
      m = L.circle([s.lat, s.lng], {
        radius: 450, color: sea, weight: 1.5, fillColor: sea, fillOpacity: 0.14,
      });
    } else {
      m = L.circleMarker([s.lat, s.lng], {
        radius: isRep ? 10 : 6, color: '#fff', weight: 2,
        fillColor: isRep ? sea : accent, fillOpacity: 0.95,
      });
    }

    m.addTo(map).bindPopup(popupHtml(s));
    m.on('click', () => selectSite(s.id, { fromMap: true }));
    markers[s.id] = m;
  });
}

function popupHtml(s) {
  return `<div class="map-popup">
    <div class="p-name">${esc(fld(s, 'name'))}</div>
    <div class="p-type">${esc(fld(s, 'type'))}${s.kind !== '대표' ? ' · ' + esc(T('map.linkedPlace')) : ''}</div>
    <div class="p-sum">${esc(fld(s, 'summary'))}</div>
    <a class="p-btn" href="#detail" data-goto="${esc(s.id)}">${esc(T('map.popupBtn'))}</a>
  </div>`;
}

// 팝업 내부 '자세히 보기' 클릭 (동적 생성 요소 → 위임)
document.addEventListener('click', (e) => {
  const link = e.target.closest('[data-goto]');
  if (link) { e.preventDefault(); selectSite(link.dataset.goto, { pan: true }); }
});

/* ========== 8. 카드 리스트 ========== */
function renderCards() {
  const list = document.getElementById('cardList');
  const items = SITES.filter((s) => activeRegion === '전체' || s.region === activeRegion);
  list.innerHTML = '';

  if (!items.length) {
    list.innerHTML = `<p class="map-fallback">${esc(T('map.empty'))}</p>`;
    return;
  }

  items.forEach((s) => {
    const b = document.createElement('button');
    b.className = 'site-card' + (s.id === activeId ? ' active' : '');
    b.id = 'card-' + s.id;
    b.setAttribute('aria-label', T('card.detailAria', { name: fld(s, 'name') }));
    b.innerHTML = `
      <div class="card-top">
        <span class="name">${esc(fld(s, 'name'))}</span>
        <span class="pill kind-${esc(s.kind)}">${esc(kindLabel(s.kind))}</span>
        <span class="pill type">${esc(fld(s, 'type'))}</span>
      </div>
      <div class="summary">${esc(fld(s, 'summary'))}</div>
      <div class="meta"><i class="fa-solid fa-location-dot"></i> ${esc(fld(s, 'region'))}${s.olle ? ` · ${esc(T('card.olle', { olle: s.olle }))}` : ''}</div>`;
    b.onclick = () => selectSite(s.id, { pan: true });
    list.appendChild(b);
  });
}

/* ========== 9. 장소 선택 → 스토리 뷰 전환 ========== */
function selectSite(id, opts = {}) {
  const s = SITES.find((x) => x.id === id);
  if (!s) return;
  activeId = id;

  // 카드 활성 상태
  document.querySelectorAll('.site-card').forEach((c) => c.classList.remove('active'));
  const card = document.getElementById('card-' + id);
  if (card) card.classList.add('active');

  // 지도 동기화
  if (map && markers[id]) {
    if (opts.pan || opts.fromMap) {
      map.setView([s.lat, s.lng], Math.max(map.getZoom(), CONFIG.focusZoom), { animate: true });
    }
    if (opts.pan) markers[id].openPopup();
  }

  renderDetail(s);
  transitionToDetail();   // 자연스러운 스크롤 전환 + 강조
}

/* 상세 섹션으로 부드럽게 이동하고 잠깐 강조 */
function transitionToDetail() {
  const section = document.getElementById('detail');
  const cardEl = document.getElementById('detailCard');
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  cardEl.classList.remove('flash');
  void cardEl.offsetWidth;         // reflow → 애니메이션 재생 보장
  cardEl.classList.add('flash');
}

function renderDetail(s) {
  const el = document.getElementById('detailCard');
  const hasStory = !!s.story;
  const notes = (s.notes || []).filter(Boolean);

  el.innerHTML = `
    <div class="detail-head">
      <h3>${esc(fld(s, 'name'))}</h3>
      <span class="pill kind-${esc(s.kind)}">${esc(kindLabel(s.kind))}</span>
      <span class="pill type">${esc(fld(s, 'type'))}</span>
    </div>
    <p class="d-summary">${esc(fld(s, 'summary'))}</p>
    <div class="d-meta">
      <div><i class="fa-solid fa-location-dot"></i>${esc(fld(s, 'region'))}</div>
      ${s.olle ? `<div><i class="fa-solid fa-shoe-prints"></i>${esc(T('detail.olle', { olle: s.olle }))}</div>` : ''}
      <div><i class="fa-solid fa-map-pin"></i>${esc(s.lat)}, ${esc(s.lng)}</div>
    </div>
    ${notes.length ? `<div class="d-note"><b>${esc(T('detail.note'))}</b> · ${notes.map(esc).join(' / ')}</div>` : ''}
    ${hasStory
      ? `<a class="btn btn-primary" href="story.html?site=${esc(s.id)}">${esc(T('detail.story'))} <i class="fa-solid fa-arrow-right"></i></a>`
      : `<button class="btn" disabled>${esc(T('detail.soon'))}</button>`}
  `;

  Glossary.apply(el);   // 상세 패널 텍스트에 용어 툴팁 적용
}

/* ========== 10. 권역 필터 → 지도 범위 ========== */
function fitToRegion() {
  if (!map) return;
  if (activeRegion === '전체') { map.setView(CONFIG.jejuCenter, CONFIG.jejuZoom); return; }
  const items = SITES.filter((s) => s.region === activeRegion);
  if (!items.length) return;
  map.fitBounds(L.latLngBounds(items.map((s) => [s.lat, s.lng])).pad(0.3));
}

/* ========== 11. 폴백 & 유틸 ========== */
function showMapFallback() {
  document.getElementById('map').innerHTML =
    '<div class="map-fallback"><i class="fa-solid fa-triangle-exclamation"></i><br>' + esc(T('map.fallback')) + '</div>';
  document.getElementById('cardList').innerHTML =
    `<p class="map-fallback">${esc(T('map.fallback'))}</p>`;
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
function escapeRegExp(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function esc(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* 전역 노출 (HTML onclick / 팝업에서 호출) */
window.selectSite = selectSite;
