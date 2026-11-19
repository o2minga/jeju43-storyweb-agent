/* ============================================================
   glossary.js — 역사 용어 사전 + 툴팁 엔진 (공용)
   index.html / story.html 양쪽에서 사용.
   window.GLOSSARY, window.Glossary 로 노출.
   ============================================================ */
'use strict';

/* 청소년·외국인 눈높이 풀이. 용어 추가는 여기에만. */
window.GLOSSARY = {
  '4·3'          : '1947~1954년 제주에서 수많은 주민이 희생된 사건. 정식 명칭은 「제주4·3사건」.',
  '토벌대'        : '무장대를 진압한다는 명목으로 투입된 군인·경찰 부대.',
  '국방경비대'    : '대한민국 정부 수립 전후의 군대로, 지금 국군의 전신.',
  '무장대'        : '산에 근거지를 두고 무장 활동을 벌인 세력.',
  '입산자'        : '토벌을 피해, 또는 무장대를 따라 산으로 들어간 사람. 그 이유로 처벌 대상이 되기도 했다.',
  '붉은기'        : '좌익·공산 세력을 상징하던 붉은 깃발. 이를 들었다는 이유가 처벌 근거로 쓰이기도 했다.',
  '초토화'        : '마을을 통째로 불태워 없애는 작전.',
  '소개령'        : '주민을 원래 살던 곳에서 강제로 다른 곳으로 옮기게 한 명령.',
  '예비검속'      : '사건을 미리 막는다는 명목으로 사람들을 붙잡아 가둔 일. 이후 학살로 이어지기도 했다.',
  '군법회의'      : '군대가 여는 재판. 4·3 당시 많은 주민이 이 절차로 형을 받았다.',
  '잃어버린 마을'  : '4·3 때 불타 사라진 뒤 끝내 복구되지 못한 마을.',
  '거욱대'        : '재앙을 막고 마을을 지키려고 세운 제주의 돌탑.',
  '올레'          : '집과 마을길을 잇는 좁은 골목길(제주 방언).',
  '수장'          : '사람을 바다에 빠뜨려 살해하는 것.',
  '해원상생'      : '맺힌 원한을 풀고(해원) 함께 살아간다(상생)는 뜻의 위령 정신.',
  '도화선'        : '큰 사건이 터지게 만든 직접적인 계기.',
  '민관총파업'    : '관공서 직원까지 함께 참여한 대규모 파업.',
  '3·1절 발포사건' : '1947년 3·1절 기념행사 뒤 경찰이 시민에게 총을 쏴 사상자가 난 사건. 4·3의 도화선이 됐다.',
};

window.Glossary = (() => {
  const DICT = window.GLOSSARY;
  let tip = null, terms = [], matcher = null;

  function init() {
    if (tip) return;                 // 중복 init 방지
    terms = Object.keys(DICT).sort((a, b) => b.length - a.length);
    matcher = new RegExp('(' + terms.map(escapeRegExp).join('|') + ')', 'g');

    tip = document.createElement('div');
    tip.id = 'glossTip';
    tip.setAttribute('role', 'tooltip');
    document.body.appendChild(tip);

    document.addEventListener('mouseover', (e) => hoverIn(e));
    document.addEventListener('mouseout', (e) => hoverOut(e));
    document.addEventListener('focusin', (e) => hoverIn(e));
    document.addEventListener('focusout', (e) => hoverOut(e));
    document.addEventListener('click', (e) => {           // 모바일 탭 토글
      const g = e.target.closest('.gloss');
      if (g) { e.preventDefault(); (tip.classList.contains('show') && tip._for === g) ? hide() : show(g); }
      else if (!e.target.closest('#glossTip')) hide();
    });
    window.addEventListener('scroll', hide, { passive: true });
    window.addEventListener('resize', hide);
  }

  const hoverIn = (e) => { const g = e.target.closest && e.target.closest('.gloss'); if (g) show(g); };
  const hoverOut = (e) => { const g = e.target.closest && e.target.closest('.gloss'); if (g) hide(); };

  function show(g) {
    const term = g.dataset.term || g.textContent.trim();
    const def = DICT[term] || g.dataset.def;
    if (!def) return;
    tip._for = g;
    tip.innerHTML = `<span class="t-term">${esc(term)}</span>${esc(def)}`;
    tip.classList.add('show');
    position(g);
  }
  function hide() { if (tip) { tip.classList.remove('show'); tip._for = null; } }

  function position(g) {
    const r = g.getBoundingClientRect();
    const tr = tip.getBoundingClientRect();
    const sx = window.scrollX, sy = window.scrollY, gap = 10;
    const above = r.top > tr.height + gap + 8;
    const top = above ? r.top + sy - tr.height - gap : r.bottom + sy + gap;
    let left = r.left + sx + r.width / 2 - tr.width / 2;
    left = Math.max(sx + 8, Math.min(left, sx + document.documentElement.clientWidth - tr.width - 8));
    tip.style.setProperty('--tip-arrow', (r.left + sx + r.width / 2 - left) + 'px');
    tip.classList.toggle('above', above);
    tip.classList.toggle('below', !above);
    tip.style.top = top + 'px';
    tip.style.left = left + 'px';
  }

  /* 루트 안 텍스트에서 사전 용어를 찾아 .gloss 로 감싼다 (링크/버튼/기존 gloss 제외) */
  function apply(root) {
    if (!root || !matcher) return;
    const skip = new Set(['SCRIPT', 'STYLE', 'A', 'BUTTON']);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        let p = node.parentElement;
        while (p && p !== root) {
          if (skip.has(p.tagName) || p.classList.contains('gloss')) return NodeFilter.FILTER_REJECT;
          p = p.parentElement;
        }
        matcher.lastIndex = 0;
        return matcher.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    const targets = [];
    while (walker.nextNode()) targets.push(walker.currentNode);

    targets.forEach((node) => {
      const frag = document.createDocumentFragment();
      let last = 0;
      matcher.lastIndex = 0;
      node.nodeValue.replace(matcher, (m, _g, idx) => {
        if (idx > last) frag.appendChild(document.createTextNode(node.nodeValue.slice(last, idx)));
        frag.appendChild(makeGloss(m));
        last = idx + m.length;
        return m;
      });
      if (last < node.nodeValue.length) frag.appendChild(document.createTextNode(node.nodeValue.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });
  }

  function makeGloss(term) {
    const span = document.createElement('span');
    span.className = 'gloss';
    span.tabIndex = 0;
    span.dataset.term = term;
    span.setAttribute('aria-label', `${term}: ${DICT[term]}`);
    span.textContent = term;
    return span;
  }

  const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  return { init, apply, show, hide };
})();
