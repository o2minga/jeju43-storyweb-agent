/* ============================================================
   chatbot.js — 캐릭터 해설사 챗봇 "동백" (스킬7 · 안내원)
   · 우측 하단 floating 캐릭터 버튼 → 채팅 패널
   · data/chatbot-kb.json 의 '검증된 사실'만으로 답변 (환각 방지 가드레일)
   · KB에 없으면 fallback("기록에 명시되지 않았습니다"), 답변엔 〔출처〕 표기
   · 관련 유적지는 지도/이야기로 연결, KO/EN 이중언어(i18n 연동)
   의존: js/i18n.js(window.I18n), (선택) js/glossary.js(window.Glossary)
   ============================================================ */
'use strict';

(function () {
  const KB_URL = 'data/chatbot-kb.json';

  /* ---------- 캐릭터 SVG (해설사 동백) ---------- */
  const AVATAR = `
  <svg class="bot-face" viewBox="0 0 64 68" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="botRobe" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#26506A"/><stop offset="1" stop-color="#1A3646"/>
      </linearGradient>
    </defs>
    <path d="M11 68 v-8 a21 21 0 0 1 42 0 v8 z" fill="url(#botRobe)"/>
    <path d="M32 47 l7 5 v10 h-14 v-10 z" fill="#EAF1F4" opacity=".92"/>
    <path d="M13 31 a19 19 0 0 1 38 0 v7 a4 4 0 0 1-4 4 v-9 a15 15 0 0 0-30 0 v9 a4 4 0 0 1-4-4 z" fill="#2C2622"/>
    <rect x="19" y="24" width="26" height="27" rx="13" fill="#F2C9A0"/>
    <circle cx="27" cy="36" r="1.9" fill="#2C2622"/>
    <circle cx="37" cy="36" r="1.9" fill="#2C2622"/>
    <path d="M28.5 42.5 q3.5 3 7 0" stroke="#B5654A" stroke-width="1.7" fill="none" stroke-linecap="round"/>
    <g transform="translate(41 55)">
      <circle r="5.4" fill="#D9584A"/>
      <circle cx="-3.4" cy="-1.4" r="3.1" fill="#E4695B"/>
      <circle cx="3.4" cy="-1.4" r="3.1" fill="#E4695B"/>
      <circle cx="-2.1" cy="2.8" r="3.1" fill="#E4695B"/>
      <circle cx="2.1" cy="2.8" r="3.1" fill="#E4695B"/>
      <circle r="2" fill="#F2C14E"/>
    </g>
  </svg>`;

  /* ---------- 상태 ---------- */
  let KB = null;
  let open = false;
  let els = {};

  /* ---------- 유틸 ---------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  // KB 문장의 리치 토큰 → HTML (출처 배지·용어·굵게·줄바꿈)
  function rich(raw) {
    let s = esc(raw);
    s = s.replace(/\{b:([^}]*)\}/g, '<b>$1</b>');
    s = s.replace(/\{g:([^}]*)\}/g, (m, t) => `<span class="gloss" tabindex="0" data-term="${t}">${t}</span>`);
    s = s.replace(/〔([^〕]*)〕/g, (m, t) => `<span class="bot-src">〔${t}〕</span>`);
    s = s.replace(/\n/g, '<br>');
    return s;
  }
  function norm(s) {
    return String(s || '').toLowerCase().replace(/[\s·.,!?~'"’()\[\]{}〔〕<>—\-]/g, '');
  }
  const t = (k, v) => (window.I18n ? window.I18n.t(k, v) : k);
  const lang = () => (window.I18n ? window.I18n.lang : 'ko');
  const persona = () => (KB && KB.persona && (KB.persona[lang()] || KB.persona.ko)) || {};

  /* ---------- 검색(RAG) : 내부 KB 우선 → 외부 신뢰 출처 인용 보강 ----------
     정책(팀 가이드라인):
       1) 내부 samples(KB.entries)에 답이 있으면 그대로 사용(검증된 사실).
       2) 없으면 '보강(grounding)' — 아래 두 경로에서만 가져온다:
          (a) 큐레이션 grounded 데이터(허용 출처·인용 포함, 오프라인 안전 기본값)
          (b) 라이브 검색 provider window.CHATBOT_GROUNDING (백엔드가 주입 시에만)
       3) 보강 답변의 인용은 반드시 '허용 출처(신뢰 기관)' 화이트리스트를 통과해야 하며,
          통과 인용이 하나도 없으면 답변을 폐기하고 폴백한다(미검증 정보 배제 = 환각 금지).
       4) 보강 답변에는 [AI 종합 연출 답변] 라벨과 [출처: 기관 / 사료·URL] 을 반드시 부착.
       5) 민감·지어내기 금지 주제는 외부 검색조차 하지 않고 담담히 우회.                      */

  // 출처 채택 기준(팀 기준): 신뢰 기관·공공기관·언론 기사 등 '출처를 남길 수 있는 자료'는 자유롭게 허용.
  // 단 (1) 출처가 없으면 배제(무출처=미검증), (2) 개인 블로그·유튜브 등 개인 UGC는 차단(denylist).
  const RELIABLE_HINTS = ['제주4·3평화재단', '국사편찬위원회', '진실화해위원회', '제주4·3연구소', '제주다크투어']; // 참고용 힌트(게이트 아님)
  const BLOCKED_HOSTS = [
    'youtube.com', 'youtu.be', 'm.youtube.com', 'tiktok.com',
    'blog.naver.com', 'cafe.naver.com', 'blog.daum.net', 'cafe.daum.net',
    'tistory.com', 'brunch.co.kr', 'velog.io', 'medium.com', 'wordpress.com', 'blogspot.com',
    'instagram.com', 'facebook.com', 'x.com', 'twitter.com', 'threads.net',
  ];
  const BLOCKED_WORDS = ['블로그', '유튜브', 'youtube', 'tistory', '인스타', '페이스북', '개인 블로그', '개인블로그'];
  const blockedList = () => (KB && KB.blockedSources) || BLOCKED_HOSTS;

  // 인용 채택: 출처 식별자(기관/사료/URL)가 있고, 차단 목록(개인 블로그·유튜브 등)이 아니면 허용.
  function isAllowedCite(c) {
    if (!c) return false;
    if (!(c.org || c.ref || c.title || c.url)) return false;              // 무출처 → 배제
    const host = String(c.url || '').replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0].toLowerCase();
    if (host && blockedList().some((h) => host.includes(h))) return false; // 개인 블로그·유튜브 등 차단
    const orgl = String(c.org || '').toLowerCase();
    if (BLOCKED_WORDS.some((w) => orgl.includes(w.toLowerCase()))) return false;
    return true;                                                          // 그 외 신뢰 기관·공공기관·기사 등 허용
  }

  function scoreEntries(list, n) {
    let best = null, bestScore = 0;
    (list || []).forEach((e) => {
      let score = 0;
      (e.tags || []).forEach((tag) => { const nt = norm(tag); if (nt && n.includes(nt)) score += Math.min(nt.length, 6); });
      ['ko', 'en'].forEach((l) => { const q = norm(e.q && e.q[l]); if (q && n.length >= 3 && (n.includes(q) || q.includes(n))) score += 5; });
      if (score > bestScore) { bestScore = score; best = e; }
    });
    return { best, bestScore };
  }

  // 외부 보강: 큐레이션 grounded → (선택) 라이브 provider. 허용 출처 인용만 남기고, 없으면 폐기.
  async function ground(input, n) {
    let cand = null;
    const g = scoreEntries(KB.grounded, n);
    if (g.best && g.bestScore >= 2) {
      cand = { text: g.best.a[lang()] || g.best.a.ko, citations: g.best.citations || [],
               synthesized: g.best.synthesized !== false, site: g.best.site || null };
    }
    if (typeof window.CHATBOT_GROUNDING === 'function') {
      try {
        const live = await window.CHATBOT_GROUNDING(input, { lang: lang(), reliableHints: RELIABLE_HINTS, blocked: blockedList() });
        if (live && live.text && Array.isArray(live.citations)) {
          cand = { text: live.text, citations: live.citations, synthesized: live.synthesized !== false, site: live.site || null };
        }
      } catch (e) { console.warn('[chatbot] 라이브 검색 실패 — 무시(폴백)', e); }
    }
    if (!cand) return null;
    cand.citations = (cand.citations || []).filter(isAllowedCite);   // 미검증 출처 배제
    if (!cand.citations.length) return null;                          // 인용 없으면 답변 폐기(환각 금지)
    return cand;
  }

  async function answer(input) {
    const n = norm(input);
    if (n.length < 1) return null;

    // 1) 민감·잔혹·지어내기 금지 주제 → 담담한 우회(외부 검색도 하지 않음)
    if (KB.sensitive && (KB.sensitive.tags || []).some((tag) => n.includes(norm(tag)))) {
      return { text: KB.sensitive.a[lang()] || KB.sensitive.a.ko, site: null, kind: 'sensitive' };
    }

    // 2) 내부 KB(검증된 사실) 우선
    const { best, bestScore } = scoreEntries(KB.entries, n);
    if (best && bestScore >= 2) {
      return { text: best.a[lang()] || best.a.ko, site: best.site || null, kind: 'answer' };
    }

    // 3) 외부 신뢰 출처로 보강(인용 필수 · [AI 종합 연출 답변] 라벨)
    const g = await ground(input, n);
    if (g) return { text: g.text, site: g.site, kind: 'grounded', citations: g.citations, ai: true };

    // 4) 폴백 — 지어내지 않음
    return { text: KB.fallback.a[lang()] || KB.fallback.a.ko, site: null, kind: 'fallback' };
  }

  // 인용 렌더: [출처: 기관, 사료명 / URL]
  function citeHtml(c) {
    const label = [c.org, c.ref || c.title].filter(Boolean).join(', ');
    const inner = c.url ? `<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(label || c.url)}</a>` : esc(label);
    return `<span class="bot-cite">[출처: ${inner}]</span>`;
  }

  /* ---------- 메시지 렌더 ---------- */
  function addMsg(who, html, opts = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'bot-msg ' + (who === 'me' ? 'from-me' : 'from-bot');
    if (who === 'bot') {
      wrap.innerHTML = `<span class="bot-mini" aria-hidden="true">${AVATAR}</span><div class="bot-bubble">${html}</div>`;
    } else {
      wrap.innerHTML = `<div class="bot-bubble">${html}</div>`;
    }
    els.log.appendChild(wrap);

    // 관련 장소 연결 (지도/이야기)
    if (opts.site) {
      const p = persona();
      const box = document.createElement('div');
      box.className = 'bot-links';
      const canSelect = typeof window.selectSite === 'function';
      const mapHref = canSelect ? '#detail' : `index.html#site=${encodeURIComponent(opts.site)}`;
      box.innerHTML =
        `<a class="bot-link" data-site-map="${esc(opts.site)}" href="${mapHref}"><i class="fa-solid fa-location-dot"></i> ${esc(p.linkMap || '지도에서 보기')}</a>` +
        `<a class="bot-link" href="story.html?site=${encodeURIComponent(opts.site)}"><i class="fa-solid fa-book-open"></i> ${esc(p.linkStory || '이야기 보기')}</a>`;
      els.log.appendChild(box);
    }

    if (window.Glossary && typeof window.Glossary.apply === 'function') {
      try { window.Glossary.apply(wrap); } catch (_) {}
    }
    els.log.scrollTop = els.log.scrollHeight;
    return wrap;
  }

  function ask(text) {
    const q = (text || '').trim();
    if (!q) return;
    addMsg('me', esc(q));
    els.input.value = '';

    // '생각 중' → 약간의 지연으로 대화 리듬 (외부 보강은 비동기)
    const thinking = addMsg('bot', `<span class="bot-typing"><i></i><i></i><i></i></span><span class="sr-only">${esc(t('bot.thinking'))}</span>`);
    setTimeout(async () => {
      let res;
      try { res = await answer(q); } catch (e) { console.error('[chatbot] answer 오류', e); res = null; }
      thinking.remove();
      if (!res) return;
      let html = rich(res.text);
      if (res.ai) html = `<span class="bot-ai-label">[AI 종합 연출 답변]</span> ` + html;   // AI 가공/추론 표기
      if (res.citations && res.citations.length) {
        html += `<div class="bot-cites">` + res.citations.map(citeHtml).join('') + `</div>`;
      }
      addMsg('bot', html, { site: res.site });
    }, 420);
  }

  /* ---------- 추천 질문 칩 ---------- */
  function renderSuggestions() {
    const p = persona();
    els.sugg.innerHTML = '';
    (p.suggestions || []).forEach((s) => {
      const b = document.createElement('button');
      b.className = 'bot-chip';
      b.type = 'button';
      b.textContent = s;
      b.addEventListener('click', () => ask(s));
      els.sugg.appendChild(b);
    });
  }

  /* ---------- 인사(대화 초기화) ---------- */
  function resetConversation() {
    const p = persona();
    els.log.innerHTML = '';
    els.name.textContent = p.name || '동백';
    els.role.textContent = p.role || '제주 4·3 해설사';
    els.input.setAttribute('placeholder', p.placeholder || t('bot.open'));
    addMsg('bot', rich(p.greeting || ''));
    renderSuggestions();
  }

  /* ---------- 열기/닫기 ---------- */
  function setOpen(v) {
    open = v;
    els.panel.classList.toggle('is-open', v);
    els.panel.setAttribute('aria-hidden', String(!v));
    els.launcher.classList.toggle('is-hidden', v);
    els.launcher.setAttribute('aria-expanded', String(v));
    if (v) {
      if (!els.log.children.length) resetConversation();
      setTimeout(() => els.input.focus(), 60);
    } else {
      els.launcher.focus();
    }
  }

  /* ---------- 보강 답변용 라벨/인용 스타일 (1회 주입) ---------- */
  function injectStyle() {
    if (document.getElementById('botGroundStyle')) return;
    const st = document.createElement('style');
    st.id = 'botGroundStyle';
    st.textContent = `
      .bot-ai-label{display:inline-block;font-size:.7em;font-weight:800;letter-spacing:.02em;
        color:#8a5a1f;background:#f3ece1;border:1px solid #e2d2ba;border-radius:6px;padding:1px 6px;margin-right:5px;vertical-align:1px}
      .bot-cites{margin-top:8px;display:flex;flex-direction:column;gap:3px}
      .bot-cite{font-size:.72em;color:#5a7385;line-height:1.5}
      .bot-cite a{color:#33454f;text-decoration:underline}`;
    document.head.appendChild(st);
  }

  /* ---------- DOM 구성 ---------- */
  function build() {
    injectStyle();
    const root = document.createElement('div');
    root.id = 'botRoot';
    root.setAttribute('data-nosnippet', '');
    root.innerHTML = `
      <button id="botLauncher" class="bot-launcher" aria-expanded="false" aria-controls="botPanel">
        <span class="bot-avatar">${AVATAR}</span>
        <span class="bot-launcher-label" data-i18n="bot.open"></span>
        <span class="bot-ping" aria-hidden="true"></span>
      </button>

      <section id="botPanel" class="bot-panel" role="dialog" aria-modal="false" aria-labelledby="botTitle" aria-hidden="true">
        <header class="bot-head">
          <span class="bot-avatar sm">${AVATAR}</span>
          <span class="bot-id">
            <b id="botTitle" class="bot-name"></b>
            <span class="bot-role"></span>
          </span>
          <button class="bot-reset" type="button" data-i18n-attr="aria-label:bot.reset; title:bot.reset"><i class="fa-solid fa-arrow-rotate-left" aria-hidden="true"></i></button>
          <button class="bot-x" type="button" data-i18n-attr="aria-label:bot.close; title:bot.close"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
        </header>
        <div class="bot-log" id="botLog" role="log" aria-live="polite"></div>
        <div class="bot-sugg" id="botSugg"></div>
        <form class="bot-input" id="botForm" autocomplete="off">
          <input id="botText" type="text" aria-label="4·3 해설사에게 질문">
          <button class="bot-send" type="submit" data-i18n-attr="aria-label:bot.send; title:bot.send"><i class="fa-solid fa-paper-plane" aria-hidden="true"></i></button>
        </form>
        <p class="bot-foot"></p>
      </section>`;
    document.body.appendChild(root);

    els = {
      root,
      launcher: root.querySelector('#botLauncher'),
      panel: root.querySelector('#botPanel'),
      log: root.querySelector('#botLog'),
      sugg: root.querySelector('#botSugg'),
      form: root.querySelector('#botForm'),
      input: root.querySelector('#botText'),
      name: root.querySelector('.bot-name'),
      role: root.querySelector('.bot-role'),
      foot: root.querySelector('.bot-foot'),
    };

    els.launcher.addEventListener('click', () => setOpen(true));
    root.querySelector('.bot-x').addEventListener('click', () => setOpen(false));
    root.querySelector('.bot-reset').addEventListener('click', resetConversation);
    els.form.addEventListener('submit', (e) => { e.preventDefault(); ask(els.input.value); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && open) setOpen(false); });

    // 지도 연결: 인덱스 페이지면 그 자리에서 선택, 아니면 링크 이동
    els.log.addEventListener('click', (e) => {
      const a = e.target.closest('[data-site-map]');
      if (a && typeof window.selectSite === 'function') {
        e.preventDefault();
        setOpen(false);
        window.selectSite(a.getAttribute('data-site-map'), { pan: true });
      }
    });

    if (window.I18n) window.I18n.apply(root);
    updateFoot();
  }

  function updateFoot() {
    const p = persona();
    if (els.foot) els.foot.textContent = p.disclaimer || '';
  }

  /* ---------- 언어 변경 대응 ---------- */
  function onLang() {
    if (!els.root) return;
    if (window.I18n) window.I18n.apply(els.root);
    updateFoot();
    if (open || els.log.children.length) resetConversation();  // 언어 섞임 방지: 재시작
  }

  /* ---------- 부팅 ---------- */
  async function init() {
    try {
      const res = await fetch(KB_URL);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      KB = await res.json();
    } catch (err) {
      console.warn('[chatbot] KB 로드 실패 — 챗봇 비활성화', err);
      return;   // 정적 사이트를 file://로 열면 KB fetch 실패 → 조용히 미표시
    }
    build();
    if (window.I18n && window.I18n.onChange) window.I18n.onChange(onLang);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
