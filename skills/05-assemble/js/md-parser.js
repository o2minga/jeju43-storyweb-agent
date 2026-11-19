/* ============================================================
   md-parser.js — 유적지 카드(.md) → story 스키마 변환기 (경로 B)
   PRD §5.2 파싱 규칙 구현. 모든 카드가 동일한 헤딩 구조를 가지므로
   이 파서 하나로 어떤 카드든 같은 템플릿(story.js)에 자동 바인딩된다.

   사용:  const story = CardParser.parse(mdText, siteMeta);
          → story.js 가 그대로 렌더할 수 있는 객체 반환
   window.CardParser 로 노출.
   ============================================================ */
'use strict';

window.CardParser = (() => {

  /* ---------- 진입점 ---------- */
  function parse(md, meta = {}) {
    const lines = md.replace(/\r\n/g, '\n').split('\n');
    const { name, region } = parseH1(lines);
    const sections = splitSections(lines);          // { 헤딩키: [줄...] }

    const basic     = tableToMap(get(sections, '기본정보'));
    const timeline  = parseTimeline(get(sections, '사건 연표'));
    const quotes    = parseQuotes(get(sections, '출처 원문'));
    const diffs     = parseTables(get(sections, '주의'));          // ⚠️주의 안의 충돌표
    const cites     = tableRows(get(sections, '출처 표기'));       // 학생용 출처 표기
    const topics    = parseBullets(get(sections, '이야기 소재'));  // 연출 이미지 캡션 재료
    const cautions  = parseBullets(get(sections, '주의'));

    const story = {
      meta: { id: meta.id || slug(name), sourceCard: meta.card || '', lang: 'ko',
              reviewStatus: 'auto-draft', generatedBy: 'md-parser.js (경로 B)' },
      hero: buildHero(name, region, basic, meta),
      sections: [],
      sources: buildSources(cites),
      notice: buildNotice(cautions),
      guardrails: { raw: cautions.map((t) => t.text) },
    };

    // 자동 생성 초안 안내 배너
    story.sections.push(section('안내', '', [
      { type: 'note', text: '이 페이지는 유적지 카드(.md)에서 {b:자동 생성된 초안}입니다. 문맥·각색은 감수 후 다듬어집니다.' },
    ]));

    story.sections.push(buildNow(basic, topics));
    story.sections.push(buildThen(timeline, quotes, diffs));
    story.sections.push(buildTrace(sections, topics));

    // 빈 섹션 제거
    story.sections = story.sections.filter((s) => s && s.blocks.length);
    return story;
  }

  /* ---------- 헤더/섹션 분해 ---------- */
  function parseH1(lines) {
    const h1 = lines.find((l) => /^#\s+/.test(l)) || '';
    const m = h1.replace(/^#\s+/, '').match(/^(.*?)\s*〔(.+?)〕/);
    if (m) return { name: clean(m[1]), region: clean(m[2].split('·')[0]) };
    return { name: clean(h1.replace(/^#\s+/, '')), region: '' };
  }

  function splitSections(lines) {
    const map = {};
    let cur = null;
    lines.forEach((l) => {
      const h = l.match(/^##\s+(.+)/);        // ## 헤딩 (### 은 섹션 내용으로 포함)
      if (h) { cur = h[1].trim(); map[cur] = []; return; }
      if (cur) map[cur].push(l);
    });
    return map;
  }

  // 헤딩 키를 키워드 부분일치로 찾음 ("출처 원문 (그대로 인용 — 수정 금지)" 등)
  function get(sections, keyword) {
    const key = Object.keys(sections).find((k) => k.includes(keyword));
    return key ? sections[key] : [];
  }

  /* ---------- 표 파서 ---------- */
  function parseTables(lines) {
    const tables = []; let buf = [];
    const flush = () => { if (buf.length >= 2) tables.push(toRows(buf)); buf = []; };
    lines.forEach((l) => { /^\s*\|/.test(l) ? buf.push(l) : flush(); });
    flush();
    return tables;
  }
  function firstTable(lines) { return parseTables(lines)[0] || null; }

  function toRows(tblLines) {
    const rows = tblLines.map((l) =>
      l.trim().replace(/^\||\|$/g, '').split('|').map((c) => clean(c)));
    // 구분선(---) 행 제거
    return rows.filter((r) => !r.every((c) => /^:?-{2,}:?$/.test(c) || c === ''));
  }
  function tableRows(lines) { const t = firstTable(lines); return t ? t.slice(1) : []; }

  function tableToMap(lines) {
    const t = firstTable(lines); const map = {};
    if (t) t.slice(1).forEach((r) => { if (r[0]) map[r[0]] = r[1] || ''; });
    return map;
  }

  /* ---------- 사건 연표 ---------- */
  function parseTimeline(lines) {
    const t = firstTable(lines); if (!t) return [];
    return t.slice(1).filter((r) => r[0]).map((r) => ({
      date: stripMd(r[0]), text: inline(r[1] || ''), source: stripMd(r[2] || ''),
    }));
  }

  /* ---------- 출처 원문 (수정 금지 = verbatim) ---------- */
  function parseQuotes(lines) {
    const out = [];
    lines.forEach((l) => {
      const m = l.match(/^\s*[-*]\s*(.+?):\s*\*\*(.+?)\*\*/);
      if (m) out.push({ source: stripMd(m[1]), text: stripMd(m[2]).replace(/^"|"$/g, '') });
    });
    return out;
  }

  /* ---------- 불릿 목록 ---------- */
  function parseBullets(lines) {
    const out = [];
    lines.forEach((l) => {
      const m = l.match(/^\s*(?:[-*]|\d+\.)\s+(.+)/);   // - * 및 번호목록(1.) 모두
      if (!m) return;
      const tm = m[1].match(/^\*\*(.+?)\*\*\s*[:：]?\s*(.*)$/);
      out.push(tm ? { title: clean(tm[1]), text: clean(tm[2]) } : { title: '', text: clean(m[1]) });
    });
    return out;
  }

  /* ================= 섹션 빌더 ================= */
  function buildHero(name, region, basic, meta) {
    const typeShort = (basic['유형'] || '').split('—')[0].split('(')[0].trim();
    return {
      region: [region, typeShort].filter(Boolean).join(' · '),
      title: name,
      subtitle: meta.summary || basic['현재 모습'] || basic['유형'] || '',
      media: { type: 'ai', src: '', flag: 'ai',
               alt: `${name}의 분위기를 상징적으로 표현한 배경 이미지`, caption: '', credit: '' },
    };
  }

  function buildNow(basic, topics) {
    const blocks = [];
    const addr = basic['주소'], type = basic['유형'], now = basic['현재 모습'], links = basic['연계 지점'];
    if (addr)  blocks.push(p(`이곳은 **${stripSrc(addr)}**에 있습니다.`, srcOf(addr)));
    if (type)  blocks.push(p(inline(type)));
    if (now)   blocks.push(p(inline(now)));
    if (links) blocks.push(p(`연계 지점 — ${inline(links)}`));

    // 연출 이미지(생성 프롬프트) 슬롯 — 카드의 '이야기 소재' 제목을 캡션 힌트로 사용
    if (topics.length) {
      blocks.push({
        type: 'gallery', columns: Math.min(topics.length, 2),
        items: topics.slice(0, 2).map((t) => ({
          src: '', flag: '연출',
          alt: `${t.title || t.text} — 상징 이미지`,
          caption: `${t.title || t.text} · 연출 이미지(생성 프롬프트 위치)`,
        })),
      });
    }
    return section('지금, 이곳', '이 장소는 어디이고, 지금은 어떤 모습일까요?', blocks);
  }

  function buildThen(timeline, quotes, diffs) {
    const blocks = [];
    if (timeline.length) blocks.push({ type: 'timeline', days: timeline });
    quotes.forEach((q) => blocks.push({ type: 'quote', style: 'default', verbatim: true, text: q.text, from: `${q.source} (원문 그대로)` }));
    // ⚠️주의 안의 충돌표 → '기록마다 다릅니다' diff
    if (diffs[0] && diffs[0].length > 1) {
      const t = diffs[0];
      blocks.push({ type: 'diff', title: '⚖️ 기록마다 다릅니다', columns: t[0], rows: t.slice(1),
        note: '같은 사건이라도 기록마다 수치·시각이 다릅니다. 이 페이지는 하나로 단정하지 않고 나란히 표기합니다.' });
    }
    return section('그날', '언제, 어떤 일이 있었을까요? (기록 기반)', blocks);
  }

  function buildTrace(sections, topics) {
    const blocks = [];
    // 현장 안내판 원문 → quote.stone (국문만, 원문 그대로)
    const signs = parseSignboards(get(sections, '현장 안내판'));
    signs.slice(0, 3).forEach((s) => blocks.push({ type: 'quote', style: 'stone', verbatim: true, text: s.text, from: s.label }));
    if (!signs.length && topics.length) blocks.push(p(inline(topics[topics.length - 1].text)));
    return section('흔적', '이 장소는 어떻게 기억되고 있을까요?', blocks);
  }

  /* 현장 안내판: **①...** / ### 〔..〕 라벨 + 이어지는 > 인용줄. [영문] 이후는 제외 */
  function parseSignboards(lines) {
    const out = []; let label = null, buf = [];
    const flush = () => { if (label && buf.length) out.push({ label, text: buf.join(' ') }); buf = []; };
    lines.forEach((l) => {
      const head = l.match(/^\*\*(.+?)\*\*/) || l.match(/^###\s+(.+)/);
      if (head) { flush(); label = clean(head[1]).replace(/〔영문[^〕]*〕/g, '').trim(); return; }
      const q = l.match(/^>\s?(.*)/);
      if (q) {
        const t = q[1];
        if (/\[영문\]|^\s*$/.test(t) && buf.length) { flush(); label = null; return; }
        if (t.trim()) buf.push(stripMd(t));
      }
    });
    flush();
    return out.filter((s) => s.text.length > 10);
  }

  /* ---------- 출처/고지 ---------- */
  function buildSources(cites) {
    return cites.filter((r) => r[0]).map((r) => ({ org: '', title: stripMd(r[0]), detail: stripMd(r[1] || '') }));
  }
  function buildNotice(cautions) {
    const base = '이 페이지의 사실 서술은 카드에 기재된 출처 기록에 근거합니다. 분위기 표현에는 [연출], 생성 이미지에는 \'AI 생성\' 표시를 붙였습니다.';
    const secret = cautions.some((c) => /외부 공개 금지|감수/.test(c.text));
    return base + (secret ? ' {b:내부 검토용 — 함께공 감수 전 외부 공개 금지.}' : '');
  }

  /* ---------- 공통 헬퍼 ---------- */
  function section(kicker, heading, blocks) { return { id: slug(kicker), kicker, heading, background: 'default', blocks: blocks.filter(Boolean) }; }
  function p(text, source) { return { type: 'p', text, source }; }

  // 마크다운 인라인 → story rich 토큰: **bold**→{b:}, 〔..〕는 남김
  function inline(s) { return clean(s).replace(/\*\*(.+?)\*\*/g, '{b:$1}'); }
  // verbatim/제목용: 마크다운 강조기호 제거
  function stripMd(s) { return clean(s).replace(/\*\*(.+?)\*\*/g, '$1').replace(/[*_`]/g, ''); }
  function stripSrc(s) { return clean(s).replace(/\s*〔[^〕]*〕/g, ''); }
  function srcOf(s) { const m = clean(s).match(/〔([^〕]*)〕/); return m ? m[1].replace(/^출처[:：]?\s*/, '') : ''; }
  function clean(s) { return String(s ?? '').trim(); }
  function slug(s) { return String(s).replace(/[^0-9a-z가-힣]+/gi, '-').toLowerCase().slice(0, 40); }

  return { parse };
})();
