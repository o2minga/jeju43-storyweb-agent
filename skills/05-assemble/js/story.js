/* ============================================================
   story.js — 스토리 상세 페이지 렌더러 (story.html)
   - ?site=<id> → data/<id>.json 을 읽어 블록 단위로 렌더
   - 시각자료(image/gallery/hero background)에 [연출]/AI 배지 자동 부착
   - reveal.js(스크롤 등장) · glossary.js(용어 툴팁) 연동
   의존: js/glossary.js, js/reveal.js
   ============================================================ */
'use strict';

const PARAMS = new URLSearchParams(location.search);
const SITE_ID = PARAMS.get('site') || 'goneuldong';
const CARD_PARAM = PARAMS.get('card');   // ?card=관덕정_카드.md → .md 직접 파싱(경로 B)

document.addEventListener('DOMContentLoaded', boot);

async function boot() {
  window.fz = fz;                       // 툴바 글자크기
  if (window.I18n) window.I18n.init();  // 언어 토글 초기화 (스토리 크롬 KO/EN)
  Glossary.init();

  let story = null;
  try {
    story = await resolveStory();
  } catch (err) {
    console.error('[story 로드 실패]', err);
    document.getElementById('story').innerHTML =
      `<div class="story-wrap" style="padding:80px 24px;text-align:center;color:var(--ink-3)">
         <p><i class="fa-solid fa-triangle-exclamation"></i></p>
         <p>이야기 데이터를 불러오지 못했습니다.<br>로컬 서버로 실행했는지, <code>?site=</code> / <code>?card=</code> 값이 올바른지 확인해 주세요.</p>
         <p><a href="index.html">← 지도로 돌아가기</a></p>
       </div>`;
    return;
  }

  document.title = `${plain(story.hero?.title) || SITE_ID} — 제주 4·3 스토리웹`;
  renderHero(story.hero);
  renderBody(story.sections || []);
  renderSources(story);

  // 등장 애니메이션 + 용어 툴팁 (동적으로 만든 DOM에 적용)
  Reveal.observe(document.getElementById('story'));
  Glossary.apply(document.getElementById('story'));
}

/* ---------- 데이터 해석: 큐레이션 JSON 우선, 없으면 카드(.md) 자동 파싱 ----------
   우선순위:
   1) ?card=<file>            → 그 .md 를 CardParser 로 파싱 (경로 B, 강제)
   2) ?site=<id> → sites.json
        a) site.story(JSON) 있으면 → 큐레이션 JSON 사용 (경로 A, 최고 품질)
        b) 없고 site.card 있으면   → 그 카드(.md) 자동 파싱 (경로 B)
        c) 둘 다 없으면            → data/<id>.json 관례 시도                       */
async function resolveStory() {
  // sites.json (메타/경로 조회용) — 없어도 진행
  let sites = [];
  try {
    const sres = await fetch('data/sites.json');
    if (sres.ok) sites = (await sres.json()).sites || [];
  } catch (_) {}

  // (1) 카드 강제 지정
  if (CARD_PARAM) {
    const meta = sites.find((s) => s.card === CARD_PARAM) || {};
    return parseCard(CARD_PARAM, meta);
  }

  // (2) site 기준
  const site = sites.find((s) => s.id === SITE_ID) || {};
  if (site.story)  return fetchJson(site.story);          // 경로 A
  if (site.card)   return parseCard(site.card, site);     // 경로 B (자동 전환의 핵심)
  return fetchJson(`data/${SITE_ID}.json`);               // 관례
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('HTTP ' + res.status + ' @ ' + url);
  return res.json();
}

async function parseCard(cardFile, meta) {
  const res = await fetch(cardFile);
  if (!res.ok) throw new Error('HTTP ' + res.status + ' @ ' + cardFile);
  const md = await res.text();
  return CardParser.parse(md, meta);                      // → story 스키마
}

/* ---------- 히어로 (배경 이미지/상징 + 배지) ---------- */
function renderHero(hero) {
  if (!hero) return;
  const el = document.getElementById('storyHero');
  const m = hero.media || { type: 'none' };
  const hasImg = m.src && m.type !== 'none';

  el.className = 'story-hero';
  if (hasImg) { el.classList.add('has-media'); el.style.setProperty('--hero-img', `url("${m.src}")`); }
  else if (m.type === 'ai' || m.type === 'photo' || m.flag === '연출') { el.classList.add('media-symbolic'); }

  el.innerHTML = `
    ${badgeHtml(m)}
    <div class="hero-inner">
      ${hero.region ? `<span class="badge">${esc(hero.region)}</span>` : ''}
      <h1>${rich(hero.title)}</h1>
      ${hero.subtitle ? `<p class="lead">${rich(hero.subtitle)}</p>` : ''}
    </div>`;
}

/* ---------- 본문 섹션 ---------- */
function renderBody(sections) {
  const root = document.getElementById('storyBody');
  root.innerHTML = sections.map(renderSection).join('');
}

function renderSection(sec) {
  const bg = sec.background && sec.background !== 'default' ? ` bg-${esc(sec.background)}` : '';
  const blocks = (sec.blocks || []).map(renderBlock).join('');
  return `
  <section class="${'section' + bg}">
    <div class="story-wrap" data-reveal-group data-reveal-step="90">
      ${sec.kicker ? `<div class="kicker reveal">${esc(sec.kicker)}</div>` : ''}
      ${sec.heading ? `<h2 class="reveal">${rich(sec.heading)}</h2>` : ''}
      ${blocks}
    </div>
  </section>`;
}

/* ---------- 블록 렌더러 (타입별) ---------- */
function renderBlock(b) {
  switch (b.type) {
    case 'p':        return `<p class="reveal">${rich(b.text)}${srcTag(b.source)}</p>`;
    case 'fx':       return `<p class="reveal"><span class="fx">${rich(b.text)}</span></p>`;
    case 'note':     return `<div class="notice reveal">${rich(b.text)}</div>`;

    case 'stats':    return renderStats(b);
    case 'timeline': return renderTimeline(b);
    case 'quote':    return renderQuote(b);
    case 'diff':     return renderDiff(b);
    case 'olle':     return renderOlle(b);
    case 'image':    return renderFigure(b, 'reveal');
    case 'gallery':  return renderGallery(b);
    default:         return '';
  }
}

function renderStats(b) {
  const cells = (b.items || []).map((it) =>
    `<div class="cell"><div class="n">${esc(it.n)}</div><div class="c">${esc(it.c)}</div></div>`).join('');
  return `
    <div class="tteum reveal" data-reveal-group data-reveal-step="70">${cells}</div>
    ${b.note ? `<p class="stat-note reveal">${rich(b.note)}${srcTag(b.source)}</p>` : ''}`;
}

function renderTimeline(b) {
  const days = (b.days || []).map((d) => `
    <div class="day" data-reveal="left">
      <div class="date">${esc(d.date)}</div>
      <p>${rich(d.text)}${srcTag(d.source)}</p>
    </div>`).join('');
  return `<div class="days" data-reveal-group data-reveal-step="120">${days}</div>`;
}

function renderQuote(b) {
  const cls = b.style === 'stone' ? 'quote stone' : 'quote';
  // verbatim(원문) 은 절대 변형하지 않음 → 이스케이프만, 리치토큰 해석 안 함
  const body = b.verbatim ? esc(b.text) : rich(b.text);
  return `<blockquote class="${cls} reveal">${body}
    ${b.from ? `<span class="from">— ${esc(b.from)}</span>` : ''}</blockquote>`;
}

function renderDiff(b) {
  const head = (b.columns || []).map((c) => `<th>${esc(c)}</th>`).join('');
  const rows = (b.rows || []).map((r) =>
    `<tr>${r.map((c, i) => i === 0 ? `<td><b>${esc(c)}</b></td>` : `<td>${esc(c)}</td>`).join('')}</tr>`).join('');
  return `
    <div class="diff reveal">
      ${b.title ? `<h3>${esc(b.title)}</h3>` : ''}
      <div class="table-scroll"><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>
      ${b.note ? `<p class="note">${rich(b.note)}</p>` : ''}
    </div>`;
}

function renderOlle(b) {
  const lines = (b.lines || []).map((l) => `<p>${rich(l.text)}${srcTag(l.source)}</p>`).join('');
  const links = (b.links || []).map((k) => `<a href="${esc(k.href)}">${esc(k.label)}</a>`).join('');
  return `
    <div class="olle reveal">
      ${b.title ? `<h3>${esc(b.title)}</h3>` : ''}
      ${lines}
      ${links ? `<div class="links">${links}</div>` : ''}
    </div>`;
}

/* ---------- 시각자료: 단일 이미지 / 갤러리 + 자동 배지 ---------- */
function renderFigure(img, extraClass = '') {
  const reveal = extraClass ? ` data-reveal="zoom"` : '';
  let inner;
  if (img.src) {
    inner = `<img src="${esc(img.src)}" alt="${esc(img.alt)}" loading="lazy">`;
  } else {
    // 이미지 자산이 아직 없을 때 — 상징 플레이스홀더(규정 위반 없음)
    inner = `<div class="media-ph"><span><i class="fa-solid fa-mountain-sun"></i>${esc(img.alt || '상징 이미지')}</span></div>`;
  }
  const cap = img.caption || img.credit
    ? `<figcaption>${esc(img.caption || '')}${img.credit ? `<span class="credit">${esc(img.credit)}</span>` : ''}</figcaption>`
    : '';
  return `
    <figure class="media"${reveal}>
      <div class="media-frame">${badgeHtml(img)}${inner}</div>
      ${cap}
    </figure>`;
}

function renderGallery(b) {
  const items = (b.items || []);
  const cols = b.columns || Math.min(items.length, 3);
  const figs = items.map((it) => renderFigure(it, '')).join('');
  return `<div class="gallery cols-${cols} reveal" data-reveal-group data-reveal-step="90">${figs}</div>`;
}

/* 시각자료 flag 에 따라 [연출]/AI 배지 자동 생성 (규정: 생성물·연출 표기 필수) */
function badgeHtml(media) {
  if (!media) return '';
  const flag = (media.flag || (media.type === 'ai' ? 'ai' : 'none'));
  if (flag === 'ai')
    return `<span class="media-badge badge-ai"><i class="fa-solid fa-wand-magic-sparkles"></i>AI 생성</span>`;
  if (flag === '연출' || flag === 'fx')
    return `<span class="media-badge badge-fx"><i class="fa-solid fa-palette"></i>연출</span>`;
  return '';
}

/* ---------- 출처 & 고지 ---------- */
function renderSources(story) {
  const el = document.getElementById('storySources');
  const items = (story.sources || []).map((s) => `
    <li>${s.org ? `<b>${esc(s.org)}</b>${s.title ? ', ' : ''}` : ''}${esc(s.title || '')}${s.detail ? ` — ${esc(s.detail)}` : ''}
      ${s.url ? ` <a href="${esc(s.url)}" target="_blank" rel="noopener">↗</a>` : ''}</li>`).join('');
  el.innerHTML = `
    <div class="story-wrap">
      <div class="kicker reveal">출처</div>
      <ul class="reveal">${items}</ul>
      ${story.notice ? `<div class="notice reveal">${rich(story.notice)}</div>` : ''}
    </div>`;
}

/* ---------- 텍스트 리치 토큰 ----------
   {b:...}  → <b>...</b>
   {g:용어} → 용어 툴팁 span (glossary.js 가 사전으로 뜻 표시)
   나머지는 이스케이프. (사전 자동 매칭은 Glossary.apply 가 추가로 처리) */
function rich(raw) {
  let s = esc(raw);
  s = s.replace(/\{b:([^}]*)\}/g, '<b>$1</b>');
  s = s.replace(/\{g:([^}]*)\}/g, (m, t) =>
    `<span class="gloss" tabindex="0" data-term="${t}">${t}</span>`);
  return s;
}
function plain(raw) { return String(raw ?? '').replace(/\{[bg]:([^}]*)\}/g, '$1'); }
function srcTag(src) { return src ? ` <span class="src">〔${esc(src)}〕</span>` : ''; }

/* ---------- 유틸 ---------- */
function fz(d) {
  const el = document.documentElement;
  let v = d === 0 ? 1 : parseFloat(el.style.getPropertyValue('--fz') || 1) + d * 0.08;
  v = Math.max(0.85, Math.min(1.4, v));
  el.style.setProperty('--fz', v.toFixed(2));
}
function esc(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
