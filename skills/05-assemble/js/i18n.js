/* ============================================================
   i18n.js — 전역 한국어/영어(KO/EN) 언어 토글 엔진 (공용)
   · 정적 크롬(히어로·섹션·푸터·툴바·챗봇 UI)을 사전으로 전환
   · data-i18n / data-i18n-html / data-i18n-attr / data-i18n-ph 지원
   · 선택은 localStorage('lang')에 저장, <html lang> 갱신
   · 언어 변경 시 window 로 'i18n:change' 이벤트 방송 → 동적 렌더러(app.js/chatbot)가 재렌더
   기획: PRD FR-09 / O4 · 신규 기획문서 스킬2("ko 채움, en 자리 확보")
   ============================================================ */
'use strict';

window.I18n = (function () {
  const STORE_KEY = 'jeju43.lang';
  const SUPPORTED = ['ko', 'en'];

  /* ---------- 사전 ---------- */
  const DICT = {
    ko: {
      /* 문서 */
      'doc.index.title': '제주 4·3 스토리웹 — 장소로 읽는 기억',
      'doc.story.title': '제주 4·3 스토리웹 — 이야기',

      /* 툴바 */
      'toolbar.fzDown': '글자 작게', 'toolbar.fzBase': '기본 크기', 'toolbar.fzUp': '글자 크게',
      'toolbar.lang': '언어 전환 (한국어/English)', 'toolbar.langLabel': 'EN',
      'toolbar.print': '인쇄',

      /* 히어로 (index) */
      'hero.badge': '제주 4·3 · 장소로 읽는 기억',
      'hero.h1': '사라진 마을, 남겨진 자리.<br>그곳에서 무슨 일이 있었을까요?',
      'hero.lead': '제주 곳곳의 4·3 유적지를 지도에서 골라, 배경지식이 없어도 이해할 수 있는 이야기로 만나보세요.',
      'hero.scroll': '아래로 내려 지도를 살펴보세요',

      /* 탐색 섹션 */
      'explore.kicker': '유적지 지도',
      'explore.title': '어디에서 시작할까요?',
      'explore.desc': '권역을 선택하거나 지도의 표시를 눌러 장소를 살펴보세요. 큰 표시는 대표 유적지, 작은 표시는 주변 연계 장소입니다.',
      'filter.all': '전체',
      'kind.대표': '대표', 'kind.연계': '연계', 'kind.부속': '부속',

      /* 상세 섹션 */
      'detail.kicker': '선택한 장소',
      'detail.title': '이 장소의 이야기',
      'detail.empty': '위 지도나 목록에서 장소를 선택하면 여기에 요약과 \'이야기 보기\'가 나타납니다.',
      'detail.story': '이야기 보기',
      'detail.soon': '이야기 준비 중',
      'detail.olle': '제주올레 {olle} 연계',
      'detail.note': '참고',
      'card.detailAria': '{name} 자세히 보기',
      'card.olle': '올레 {olle}',
      'map.popupBtn': '자세히 보기',
      'map.linkedPlace': '연계 장소',
      'map.fallback': '지도 데이터를 불러오지 못했습니다. 로컬 서버로 실행해 주세요 (예: python -m http.server).',
      'map.empty': '해당 권역의 장소가 없습니다.',

      /* 푸터 */
      'footer.srcTitle': '출처 · 자료',
      'footer.src1': '<b>제주4·3평화재단</b>, 『제주4·3사건일지』 · 『한눈에 보는 4·3』 — 사건 기록 원문',
      'footer.src2': '<b>(사)제주다크투어 · 제주4·3연구소</b>, 「제주지역 다크투어 유적지 국·영문 안내판 조사보고서」(개정판, 2020 현장조사) — 유적지 개요·좌표·안내판 채록',
      'footer.src3': '<b>현장 안내판 · 표석 · 비문</b> — 위 조사보고서 채록 원문',
      'footer.src4': '<b>제주올레 × 4·3 유적지</b> 코스별 연계 안내',
      'footer.policy1': '이 사이트의 모든 사실 서술은 신뢰할 수 있는 기관 자료에 근거합니다. 개인 블로그·유튜브 등은 출처로 사용하지 않았습니다.',
      'footer.legendFx': '분위기·상상을 더한 표현',
      'footer.legendAi': '생성형 이미지 (기록 사진 아님)',
      'footer.policy2': '잔인한 피해 장면의 직접 묘사, 실존 인물의 얼굴 복원·복제는 하지 않습니다. 기록이 서로 다를 때는 하나로 단정하지 않고 나란히 표기합니다.',
      'footer.warn': '내부 검토용 · 함께공 감수 전 외부 공개 금지',

      /* 스토리 내비 */
      'nav.toMap': '지도로',

      /* 챗봇 공통 */
      'bot.open': '4·3 해설사에게 물어보기',
      'bot.close': '닫기',
      'bot.send': '보내기',
      'bot.you': '나',
      'bot.thinking': '기록을 살펴보는 중…',
      'bot.reset': '처음으로',
    },
    en: {
      'doc.index.title': 'Jeju 4·3 Story Web — Memory read through place',
      'doc.story.title': 'Jeju 4·3 Story Web — Story',

      'toolbar.fzDown': 'Smaller text', 'toolbar.fzBase': 'Default size', 'toolbar.fzUp': 'Larger text',
      'toolbar.lang': 'Switch language (한국어/English)', 'toolbar.langLabel': '한국어',
      'toolbar.print': 'Print',

      'hero.badge': 'Jeju 4·3 · Memory read through place',
      'hero.h1': 'Vanished villages, the ground they left behind.<br>What happened in these places?',
      'hero.lead': 'Choose a Jeju 4·3 memorial site on the map and meet it as a story you can follow with no background knowledge.',
      'hero.scroll': 'Scroll down to explore the map',

      'explore.kicker': 'Site map',
      'explore.title': 'Where shall we begin?',
      'explore.desc': 'Pick a region or tap a marker on the map. Larger markers are principal sites; smaller ones are linked nearby places.',
      'filter.all': 'All',
      'kind.대표': 'Principal', 'kind.연계': 'Linked', 'kind.부속': 'Sub-site',

      'detail.kicker': 'Selected place',
      'detail.title': 'The story of this place',
      'detail.empty': 'Select a place on the map or in the list above, and its summary and a \'Read the story\' link will appear here.',
      'detail.story': 'Read the story',
      'detail.soon': 'Story coming soon',
      'detail.olle': 'Jeju Olle {olle} connection',
      'detail.note': 'Note',
      'card.detailAria': 'View details for {name}',
      'card.olle': 'Olle {olle}',
      'map.popupBtn': 'View details',
      'map.linkedPlace': 'linked place',
      'map.fallback': 'Could not load map data. Please run via a local server (e.g., python -m http.server).',
      'map.empty': 'No places in this region.',

      'footer.srcTitle': 'Sources & references',
      'footer.src1': '<b>Jeju 4·3 Peace Foundation</b>, <i>Chronicle of the Jeju 4·3 Incident</i> · <i>Jeju 4·3 at a Glance</i> — primary event records',
      'footer.src2': '<b>Jeju Dark Tours · Jeju 4·3 Research Institute</b>, "Survey Report on the Korean·English Information Signs of Jeju Dark-Tour Sites" (rev. ed., 2020 field survey) — site overviews, coordinates, sign transcriptions',
      'footer.src3': '<b>On-site information boards · markers · inscriptions</b> — original transcriptions cited in the report above',
      'footer.src4': '<b>Jeju Olle × 4·3 sites</b> — course-linked guidance',
      'footer.policy1': 'Every factual statement on this site is based on trustworthy institutional records. Personal blogs, YouTube, and the like are not used as sources.',
      'footer.legendFx': 'Atmospheric / imaginative expression',
      'footer.legendAi': 'AI-generated image (not a documentary photo)',
      'footer.policy2': 'We do not directly depict cruel scenes of harm, nor reconstruct or replicate the faces of real individuals. Where records differ, we present them side by side rather than fixing on one.',
      'footer.warn': 'Internal review only · Do not publish externally before Hamkkegong review',

      'nav.toMap': 'To map',

      'bot.open': 'Ask the 4·3 guide',
      'bot.close': 'Close',
      'bot.send': 'Send',
      'bot.you': 'You',
      'bot.thinking': 'Looking through the records…',
      'bot.reset': 'Restart',
    },
  };

  /* ---------- 상태 ---------- */
  let lang = detectInitial();

  function detectInitial() {
    try {
      const saved = localStorage.getItem(STORE_KEY);
      if (saved && SUPPORTED.includes(saved)) return saved;
    } catch (_) {}
    const htmlLang = (document.documentElement.getAttribute('lang') || '').slice(0, 2);
    return SUPPORTED.includes(htmlLang) ? htmlLang : 'ko';
  }

  /* ---------- 조회 ---------- */
  function t(key, vars) {
    let s = (DICT[lang] && DICT[lang][key]);
    if (s == null) s = (DICT.ko && DICT.ko[key]) != null ? DICT.ko[key] : key;
    if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? vars[k] : m));
    return s;
  }

  /* 데이터 객체에서 현재 언어 필드를 고른다: pick(site,'summary') → summary_en(있으면) / summary */
  function pick(obj, field) {
    if (!obj) return '';
    if (lang !== 'ko') {
      const v = obj[field + '_en'];
      if (v != null && v !== '') return v;
    }
    return obj[field] != null ? obj[field] : '';
  }

  /* ---------- DOM 적용 ---------- */
  function apply(root) {
    const scope = root || document;

    scope.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    scope.querySelectorAll('[data-i18n-html]').forEach((el) => {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
    scope.querySelectorAll('[data-i18n-ph]').forEach((el) => {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-ph')));
    });
    scope.querySelectorAll('[data-i18n-attr]').forEach((el) => {
      // 형식: "aria-label:key; title:key2"
      el.getAttribute('data-i18n-attr').split(';').forEach((pair) => {
        const [attr, key] = pair.split(':').map((x) => x && x.trim());
        if (attr && key) el.setAttribute(attr, t(key));
      });
    });
  }

  /* ---------- 전환 ---------- */
  function set(next) {
    if (!SUPPORTED.includes(next) || next === lang) {
      if (next === lang) broadcast();       // 첫 배선 시 강제 렌더에도 사용
      return;
    }
    lang = next;
    try { localStorage.setItem(STORE_KEY, lang); } catch (_) {}
    document.documentElement.setAttribute('lang', lang);
    apply(document);
    broadcast();
  }
  function toggle() { set(lang === 'ko' ? 'en' : 'ko'); }

  const listeners = [];
  function onChange(fn) { if (typeof fn === 'function') listeners.push(fn); }
  function broadcast() {
    listeners.forEach((fn) => { try { fn(lang); } catch (e) { console.error(e); } });
    window.dispatchEvent(new CustomEvent('i18n:change', { detail: { lang } }));
  }

  /* ---------- 토글 버튼 자동 배선 ---------- */
  function initToggleButton() {
    const btn = document.getElementById('langToggle');
    if (!btn) return;
    const refresh = () => {
      btn.textContent = t('toolbar.langLabel');            // 다음 언어 라벨(현재 ko면 "EN")
      btn.setAttribute('aria-label', t('toolbar.lang'));
      btn.setAttribute('title', t('toolbar.lang'));
    };
    btn.addEventListener('click', () => { toggle(); refresh(); });
    onChange(refresh);
    refresh();
  }

  /* ---------- 부팅 ---------- */
  function init() {
    document.documentElement.setAttribute('lang', lang);
    apply(document);
    initToggleButton();
    broadcast();          // 동적 렌더러가 초기 언어로 그리도록
  }

  return { init, apply, set, toggle, t, pick, onChange, get lang() { return lang; } };
})();
