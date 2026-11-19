/* ============================================================
   pipeline-adapter.js — 파이프라인 samples → 웹앱 데이터 계약 어댑터
   ------------------------------------------------------------
   목적: 기존 디자인/JS(app.js·story.js·chatbot.js·glossary·md-parser)를
        "한 줄도 고치지 않고" samples/*.json (01~04·07 스킬 출력)을 화면에 바인딩.

   방법: window.fetch 를 감싸(shim) 앱이 원래 요청하던 3개 URL을 가로채고,
        samples 를 앱이 기대하는 스키마로 변환해 돌려준다. 그 외 요청(타일 등)은 그대로 통과.
          data/sites.json       ← 06(장소 목록) + 02(장소명)      → 지도/카드 인덱스
          data/<id>.json        ← 02(이야기·타임라인·출처) + 03(비주얼) + 04(오디오)
          data/chatbot-kb.json  ← 07(KB·가드레일)                → 챗봇 '동백'

   공통 규칙 반영:
     · [연출]/AI 표기 — 03 asset(gate/is_ai_generated) → story media.flag('연출'|'ai'),
       문헌(archival)은 배지 없이 credit(출처)만. (story.js badgeHtml 그대로 사용)
     · 출처 표기 — 문장 source → 〔출처〕(story.js srcTag), 하단 sources 목록, 챗봇 답변 〔출처〕
     · 지어내기 금지 — samples에 없는 값은 채우지 않음. region은 섬 단위 '제주'로만.
     · 충돌 병기 — conflicts_carried_forward → diff('기록마다 다릅니다'), precision → note
     · 오디오 — 앱에 오디오 블록 렌더러가 없음(구조 유지) → note 블록으로 정직하게 안내만.

   이 파일은 i18n/app/story/chatbot 보다 "먼저" 로드되어야 fetch shim이 선설치된다.
   ============================================================ */
'use strict';

(function () {
  /* samples 위치: 앱 HTML(/skills/05-assemble/*.html) 기준 상대경로 → 서버 루트와 무관하게 동작 */
  const BASE = '../../samples/';
  const FILES = {
    story:   BASE + '02-story-output-example.json',
    visual:  BASE + '03-visual-output-example.json',
    audio:   BASE + '04-audio-output-example.json',
    chatbot: BASE + '07-chatbot-output-example.json',
    index:   BASE + '06-map-input-example.json',
  };

  const realFetch = window.fetch.bind(window);
  let cache = null;

  async function loadSamples() {
    if (cache) return cache;
    const out = {};
    await Promise.all(Object.entries(FILES).map(async ([k, url]) => {
      try { const r = await realFetch(url); out[k] = r.ok ? await r.json() : null; }
      catch (_) { out[k] = null; }
    }));
    cache = out;
    return out;
  }

  /* ---------- 언어 필드 헬퍼 (samples는 {ko,en}, 지금은 ko만 채움) ---------- */
  const ko = (o) => (o && typeof o === 'object' ? (o.ko || '') : (o || ''));
  const en = (o) => (o && typeof o === 'object' ? (o.en || '') : '');

  /* ============ 1) data/sites.json (지도·카드 인덱스) ============ */
  /* 데모용 영어 폴백 — samples의 en이 비어 있을 때만 사용(실 파이프라인은 02/06의 en으로 대체). */
  const EN_DEMO = {
    gwandeokjeong: { name: 'Gwandeokjeong', summary: 'A symbolic place that shows where and how the Jeju April 3 began.' },
    example_place_2: { name: 'Another site (example — replace when a real card is added)', summary: 'A sample pin showing that adding a place simply adds one more marker.' },
  };

  function buildSites(s) {
    const places = (s.index && s.index.places) || [];
    const storyLoc = s.story && s.story.location_id;
    const sites = places.map((p) => {
      const hasStory = !!(storyLoc && p.location_id === storyLoc); // 실제 스토리 데이터가 있는 장소만
      const demo = EN_DEMO[p.location_id] || {};
      return {
        id: p.location_id,
        lat: p.coord && p.coord.lat,
        lng: p.coord && p.coord.lng,
        name: ko(p.name), name_en: en(p.name) || demo.name || '',
        summary: ko(p.one_liner), summary_en: en(p.one_liner) || demo.summary || '',
        region: '제주', region_en: 'Jeju',           // 섬 단위(항상 참) — 좌표 밖 지역명은 지어내지 않음
        type: '4·3 유적지', type_en: 'April 3 site',
        kind: hasStory ? '대표' : '연계',
        story: hasStory ? `data/${p.location_id}.json` : undefined, // shim이 buildStory로 응답
      };
    });
    return { sites };
  }

  /* ============ 2) data/<id>.json (스토리) ============ */
  function mediaFrom(a) {
    const isArch = a.type === 'archival';
    // 03 asset → 배지 flag: 재현금지 우회(converted)=연출, 그 외 AI=ai, 문헌=none(배지 없음·credit만)
    const flag = isArch ? 'none' : (a.gate === 'converted' ? '연출' : (a.is_ai_generated ? 'ai' : 'none'));
    // 로컬 샘플 경로(output/...)는 실제 파일이 없음 → src '' 로 두면 story.js가 상징 플레이스홀더 렌더
    const src = a.path && /^(https?:|data:)/.test(a.path) ? a.path : '';
    return {
      type: isArch ? 'photo' : 'ai',
      src, flag,
      alt: ko(a.caption) || '상징 이미지',
      caption: ko(a.caption) || '',
      credit: isArch ? (a.source || '') : '',
    };
  }

  function buildStory(s, id) {
    const st = s.story || {};
    const story = st.story || {};
    const vis = (s.visual && s.visual.assets) || [];
    const aud = s.audio || {};
    const place = ((s.index && s.index.places) || []).find((p) => p.location_id === id) || {};

    const heroAsset = vis.find((a) => a.gate === 'passed' && a.is_ai_generated)
                   || vis.find((a) => a.type !== 'archival') || vis[0] || null;

    const hero = {
      region: '제주 · 4·3 유적지',
      title: ko(st.location_name) || ko(place.name) || id,
      subtitle: ko(place.one_liner) || '',
      media: heroAsset ? mediaFrom(heroAsset)
                       : { type: 'ai', src: '', flag: 'ai', alt: '상징 이미지', caption: '', credit: '' },
    };

    const sections = [];

    /* (1) 들어가며 — intro */
    if (story.intro) {
      sections.push(section('들어가며', '', [ { type: 'p', text: ko(story.intro) } ]));
    }

    /* (2) 그날 — development + 병기/정밀도 + 타임라인 + 생성 비주얼 */
    {
      const blocks = [];
      if (story.development) {
        const src = (st.sources_by_sentence && st.sources_by_sentence[0] && st.sources_by_sentence[0].source) || '';
        blocks.push({ type: 'p', text: ko(story.development), source: src });
      }
      (st.precision_guardrails_applied || []).forEach((g) => {
        blocks.push({ type: 'note', text: `{b:기록마다 다를 수 있어 단정하지 않았습니다.} ${g.topic} — ${g.how_handled}` });
      });
      (st.conflicts_carried_forward || []).forEach((c) => {
        if (c.values && c.values.length) {
          blocks.push({ type: 'diff', title: '⚖️ 기록마다 다릅니다',
            columns: ['기록', '값'], rows: c.values.map((v) => [v.source || '', v.value || '']),
            note: c.how_handled || '하나로 단정하지 않고 나란히 표기합니다.' });
        }
      });
      if ((st.timeline_events || []).length) {
        blocks.push({ type: 'timeline', days: st.timeline_events.map((e) => ({
          date: e.date || '시기 불명',
          text: ko(e.title) + (ko(e.description) ? ` — ${ko(e.description)}` : ''),
          source: e.source || '',
        })) });
      }
      const gallery = vis.filter((a) => a !== heroAsset && a.type !== 'archival');
      if (gallery.length) {
        blocks.push({ type: 'gallery', columns: Math.min(gallery.length, 2), items: gallery.map(mediaFrom) });
      }
      sections.push(section('그날', '무슨 일이 있었을까요?', blocks, 'sea'));
    }

    /* (3) 오디오 — 전용 렌더러가 없어(구조 유지) note 로만 정직하게 안내 */
    if (aud.narration && aud.narration.path) {
      sections.push(section('오디오 가이드', '낭독으로 듣기', [
        { type: 'note', text: `{b:🎧 낭독 오디오가 제공됩니다.} AI TTS 내레이션과 자체 생성 BGM(모두 생성물 — ‘AI 생성’ 표기 대상). 오디오 파일: ${esc(aud.narration.path)}` },
      ]));
    }

    /* (4) 흔적 — closing + 문헌 이미지 */
    {
      const blocks = [];
      if (story.closing) blocks.push({ type: 'p', text: ko(story.closing) });
      const arch = vis.find((a) => a.type === 'archival');
      if (arch) { const mf = mediaFrom(arch); mf.type = 'image'; blocks.push(mf); } // type='image' 로 renderBlock 스위치 매칭
      sections.push(section('흔적', '왜 지금까지 기억될까요?', blocks));
    }

    /* 출처: 문장 출처 + 문헌 이미지 출처 (AI 생성물은 대장 제외 규칙 → 넣지 않음) */
    const srcMap = new Map();
    (st.sources_by_sentence || []).forEach((x) => { if (x.source) srcMap.set(x.source, { title: x.source, detail: '본문 사실 서술' }); });
    const arch = vis.find((a) => a.type === 'archival');
    if (arch && arch.source) srcMap.set(arch.source, { title: arch.source, detail: '문헌 이미지' });

    const pf = st.publication_flag || {};
    const notice = (pf.internal_only ? '{b:내부 검토용 — 함께공 감수 전 외부 공개 금지.} ' : '')
      + '사실 서술은 위 출처 기록에 근거합니다. 생성 이미지·영상·오디오에는 [연출]/‘AI 생성’ 표기를 붙였고, 기록이 서로 다를 때는 하나로 단정하지 않고 나란히 표기합니다.';

    return {
      meta: { id, generatedBy: 'pipeline-adapter.js (samples 02·03·04)' },
      hero,
      sections: sections.filter((x) => x && x.blocks && x.blocks.length),
      sources: [...srcMap.values()],
      notice,
    };
  }

  function section(kicker, heading, blocks, background) {
    return { kicker, heading, background: background || 'default', blocks: (blocks || []).filter(Boolean) };
  }

  /* ============ 3) data/chatbot-kb.json (챗봇 '동백') ============ */
  function buildKB(s) {
    const cb = s.chatbot || {};
    const kb = cb.kb || [];
    const gr = cb.guardrail || {};
    const fbKo = (gr.fallback_answer && gr.fallback_answer.ko) || '기록에 명시되지 않은 내용입니다.';
    const fbEn = (gr.fallback_answer && gr.fallback_answer.en) || 'This is not specified in the records.';

    const entries = kb.map((it) => {
      const hasRealSrc = it.source && !/해당 없음|없음/.test(it.source);
      return {
        q: { ko: (it.question && it.question.ko) || '', en: (it.question && it.question.en) || '' },
        a: {
          ko: ((it.answer && it.answer.ko) || '') + (hasRealSrc ? ` 〔${it.source}〕` : ''),
          en: (it.answer && it.answer.en) || '',
        },
        tags: it.tags || [],
        site: s.story && s.story.location_id ? s.story.location_id : undefined,
      };
    });

    // 거절(민감·지어내기 금지) 키워드 — forbidden_topics/refuse_topics에서 파생
    const sensitive = {
      tags: ['누구', '쏜', '가해자', '발포 명령', '생사', '살아', '죽었', '몇 명', '몇명'],
      a: { ko: fbKo, en: fbEn },
    };

    const persona = {
      ko: {
        name: '동백', role: '제주 4·3 해설사',
        greeting: '안녕하세요, 저는 4·3 해설사 동백이에요. 검증된 기록 안에서 아는 만큼만 안내해 드릴게요. 무엇이 궁금하세요?',
        placeholder: '예: 이곳에서 무슨 일이 있었나요?',
        suggestions: kb.map((i) => i.question && i.question.ko).filter(Boolean),
        disclaimer: '검증된 기록에 없는 내용은 “기록에 명시되지 않았습니다”라고 답합니다.',
        linkMap: '지도에서 보기', linkStory: '이야기 보기',
      },
      en: {
        name: 'Dongbaek', role: 'Jeju 4·3 guide',
        greeting: 'Hello, I am Dongbaek, a Jeju 4·3 guide. I answer only within verified records. What would you like to know?',
        placeholder: 'e.g., What happened here?',
        suggestions: kb.map((i) => i.question && i.question.en).filter(Boolean),
        disclaimer: 'If it is not in the records, I will say so honestly.',
        linkMap: 'View on map', linkStory: 'Read the story',
      },
    };

    // 출처 정책(팀 기준): 신뢰 기관·공공기관·기사 등 출처만 남기면 자유롭게 허용, 개인 블로그·유튜브는 차단.
    // allowedSources = 참고용 신뢰 출처 힌트(게이트 아님), blockedSources = 차단 도메인(denylist).
    const allowedSources = ['제주4·3평화재단', '국사편찬위원회', '진실화해위원회', '제주4·3연구소', '제주다크투어'];
    const blockedSources = [
      'youtube.com', 'youtu.be', 'tiktok.com', 'blog.naver.com', 'cafe.naver.com',
      'tistory.com', 'brunch.co.kr', 'velog.io', 'medium.com', 'blogspot.com',
      'instagram.com', 'facebook.com', 'x.com', 'twitter.com',
    ];

    // 큐레이션 grounded — 내부 KB에 없을 때 보강할 '허용 출처·인용 포함' 배경지식(오프라인 안전 기본값).
    // 라이브 검색 백엔드(window.CHATBOT_GROUNDING)가 있으면 그쪽 결과로 대체된다.
    // ⚠ 여기에는 신뢰 기관이 공표한 '확립된 사실'만, 반드시 인용과 함께 넣는다(추측 금지).
    const grounded = [
      {
        tags: ['4·3', '사삼', '무엇', '뭐', '정의', '기간', '언제부터', '언제까지'],
        a: {
          ko: '「제주4·3사건」은 1947년 3월 1일을 기점으로, 1948년 4월 3일 발생한 소요사태와 그 진압 과정에서 1954년 9월 21일까지 제주도에서 많은 주민이 희생된 사건을 말합니다.',
          en: 'The “Jeju April 3 Incident” refers to events beginning on March 1, 1947, through the uprising of April 3, 1948 and its suppression, during which many Jeju residents were killed until September 21, 1954.',
        },
        citations: [ { org: '제주4·3평화재단', ref: '제주4·3사건 진상조사보고서', url: 'https://jeju43peace.or.kr' } ],
        synthesized: true,
      },
    ];

    return {
      persona, sensitive, entries, grounded, allowedSources, blockedSources,
      grounding: { liveProvider: 'window.CHATBOT_GROUNDING (선택, 백엔드 주입)' },
      fallback: { a: { ko: fbKo, en: fbEn } },
    };
  }

  /* ---------- 유틸 ---------- */
  function esc(str) {
    return String(str == null ? '' : str).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function json(obj) {
    return new Response(JSON.stringify(obj), { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
  }

  /* ---------- fetch shim ---------- */
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    try {
      if (/(^|\/)data\/sites\.json(\?|$)/.test(url)) {
        return json(buildSites(await loadSamples()));
      }
      if (/(^|\/)data\/chatbot-kb\.json(\?|$)/.test(url)) {
        return json(buildKB(await loadSamples()));
      }
      const m = url.match(/(^|\/)data\/([^/]+)\.json(\?|$)/);
      if (m) {
        return json(buildStory(await loadSamples(), decodeURIComponent(m[2])));
      }
    } catch (e) {
      console.error('[pipeline-adapter] 변환 실패:', url, e);
    }
    return realFetch(input, init);
  };

  // 디버깅/재사용용 노출
  window.PipelineAdapter = { loadSamples, buildSites, buildStory, buildKB };
})();
