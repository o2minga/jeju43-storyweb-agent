/*
 * 07-chatbot — 자기완결 모달 스크립트 (goneuldong)
 * 05-assemble은 이 파일을 <script src="chatbot-modal.js"></script>로 삽입만 하면 된다.
 * KB/가드레일 데이터는 이 파일 안에 내장되어 있어 별도 fetch가 필요 없다.
 *
 * 답변 근거 범위: 추천 질문(KB) 몇 개로 한정하지 않고, 01-verify.json의 verified_facts·
 * verbatim_quotes 전체(=카드 내용 전체)를 검색 대상으로 삼는다. 카드에 없는 내용은 여전히
 * fallback으로만 답한다(지어내기 금지).
 *
 * 다국어: 메인 화면(index.html)의 EN/KO 토글이 저장한 document.documentElement.lang을 그대로
 * 따른다. 영문 FACTS/QUOTES는 한국어 원문(01-verify.json)의 사실·수치를 그대로 두고 표현만
 * 옮긴 번역이다 — QUOTES의 영문판은 "verbatim"(원문 그대로) 보증이 한국어 원문에만 적용되므로
 * source에 [translated]를 표시해 정직하게 구분한다.
 *
 * 한계: 이 매칭은 클라이언트 사이드 키워드 스코어링이다 — 실제 LLM 기반 RAG가 아니라
 * 07 스킬이 정의한 KB/가드레일 규칙을 정적 사이트에서도 동작하게 구현한 간이 버전이다.
 */
(function () {
  "use strict";

  var DATA = {
    ko: {
      KB: [
        {
          qa_id: "kb-01",
          question: "곤을동은 어떤 곳인가요?",
          answer: "제주시 화북동 바닷가에 있던, 700년이 넘는 오래된 마을이었습니다. 4·3 때 마을이 불에 타 없어진 뒤 끝내 복구되지 못해 '잃어버린 마을'로 불립니다.",
          source: "안내판 조사보고서·곤을동 표석"
        },
        {
          qa_id: "kb-02",
          question: "곤을동에서 무슨 일이 있었나요?",
          answer: "1949년 1월 4일과 5일 이틀에 걸쳐 토벌대가 마을을 포위하고 주민들을 학살한 뒤 마을 전체를 불태웠습니다. 최소 10여 명이 목숨을 잃었습니다(표석에는 24명으로 다르게 기록되어 있습니다).",
          source: "잃어버린 마을 안내판·곤을동 표석"
        },
        {
          qa_id: "kb-03",
          question: "마을에 가구가 몇 채나 있었나요?",
          answer: "잃어버린 마을 안내판에는 67가구(안곤을 22+가운데곤을 17+밧곤을 28), 곤을동 표석에는 43호로 적혀 있어 기록마다 다릅니다.",
          source: "잃어버린 마을 안내판·곤을동 표석"
        },
        {
          qa_id: "kb-04",
          question: "지금 곤을동에는 무엇이 남아 있나요?",
          answer: "집터와 올레(집과 마을길을 잇는 작은 길)가 남아 있고, '잃어버린 마을' 안내판과 곤을동 표석(2003), 2004년에 세워진 '4·3 해원 상생 거욱대'가 마을을 기억하고 있습니다.",
          source: "안내판 조사보고서·현장 안내판"
        }
      ],
      // hint: 답변 완료 후 "관련 질문" 칩으로 보여줄 때만 쓰는 자연스러운 질문 문구 —
      // 매칭 점수 계산에는 쓰지 않는다(스코어링은 여전히 text 문장 자체로만).
      FACTS: [
        { id: "f-01", text: "곤을동 옛터(잃어버린 마을)는 제주특별자치도 제주시 화북1동 4440번지 일대에 있다.", source: "안내판 조사보고서", hint: "곤을동 옛터는 어디에 있나요?" },
        { id: "f-02", text: "곤을동의 좌표는 북위 33.521722, 동경 126.557375이다.", source: "안내판 조사보고서 현장 기록", hint: "곤을동의 정확한 좌표는 어디인가요?" },
        { id: "f-03", text: "곤을동은 4·3 당시 초토화로 사라진 뒤 끝내 복구되지 못한 '잃어버린 마을'이다. 현재 집터 등 마을 흔적이 비교적 잘 남아 있으며, '잃어버린 마을' 안내판과 '4·3 해원 상생 거욱대'(2004)가 설치되어 있고 영문 안내판도 있다.", source: "안내판 조사보고서", hint: "곤을동은 지금 어떤 상태인가요?" },
        { id: "f-04", text: "4·3 이전 곤을동은 화북천 두 지류를 사이에 두고 안곤을(22가구)·가운데곤을(17가구)·밧곤을(28가구), 세 뜸(작은 동네)으로 이루어져 있었다.", source: "잃어버린 마을 안내판·안내판 조사보고서", hint: "4·3 이전 곤을동은 어떤 마을이었나요?" },
        { id: "f-05", text: "1949년 1월 4일 오후 3~4시경, 국방경비대 제2연대 1개 소대가 곤을동을 포위해 주민들을 모이게 한 뒤 젊은 사람 10여 명을 바닷가로 끌고 가 학살하고, 안곤을 22가구와 가운데곤을 17가구를 모두 불태웠다.", source: "잃어버린 마을 안내판·안내판 조사보고서", hint: "1949년 1월 4일에 무슨 일이 있었나요?" },
        { id: "f-06", text: "1949년 1월 5일, 인근 화북초등학교에 가둬두었던 주민 일부를 화북동 동쪽 바닷가 '영디밑'에서 학살하고, 밧곤을 28가구도 모두 불태웠다. 그 뒤로 곤을동은 인적이 끊겼다.", source: "잃어버린 마을 안내판·안내판 조사보고서", hint: "1949년 1월 5일에는 무슨 일이 있었나요?" },
        { id: "f-07", text: "토벌대에 의해 이틀에 걸쳐 최소 10여 명의 주민이 학살되고 마을이 전소되었으며, 끝내 복구되지 못해 '잃어버린 마을'이 되었다.", source: "안내판 조사보고서", hint: "이 사건으로 마을은 어떻게 되었나요?" },
        { id: "f-08", text: "2004년 4월 5일, (사)한국민족예술인총연합 제주도지회가 마을을 기억하기 위한 '4·3 해원 상생 거욱대'를 세웠다.", source: "현장 안내판(거욱대 비문)", hint: "거욱대는 왜, 누가 세웠나요?" },
        { id: "f-09", text: "2003년 4월 3일, 제주4·3사건진상규명및희생자명예회복실무위원회 위원장과 제주도지사가 곤을동 표석을 세웠다. 표석에는 곤을마을이 고려 충렬왕 26년(1300년)에 별도현에 속했다는 기록이 있을 만큼 700년이 넘는 유서 깊은 마을이라는 내용도 담겨 있다.", source: "현장 안내판(곤을동 표석)", hint: "곤을동 표석에는 어떤 내용이 담겨 있나요?" },
        { id: "f-10", text: "올레 18코스가 곤을동 마을 터를 지나며, 안내에는 \"초토화 작전으로 마을 전체가 불타 사라진 곤을동을 지납니다\"라고 되어 있다. 같은 코스에 4·3의 도화선이 된 관덕정도 있다.", source: "올레길 × 4·3 유적지 코스별 안내", hint: "올레길과 곤을동은 어떤 관계가 있나요?" },
        { id: "f-11", text: "1949년 2월 27일, 제2연대가 화북리에서 군법회의 사형선고자 39명의 사형을 집행했다. 정확한 집행 장소는 카드에 특정되어 있지 않다.", source: "제주4·3사건일지", hint: "화북리에서 또 다른 사건이 있었나요?" }
      ],
      QUOTES: [
        { id: "q-01", text: "토벌대, 제주읍 화북리 곤을동 주민을 이틀에 걸쳐 집단총살", source: "제주4·3사건일지 (1949-01-04)" },
        { id: "q-02", text: "곤을동은 제주시 화북1동 서쪽 바닷가에 있던 마을이다.", source: "잃어버린 마을(곤을동) 안내판" },
        { id: "q-03", text: "집과 사람은 오간데 없고 그 돌담만 남아 이 억울하고 원통한 사실을 기억하게 하는 곤을동 초토화 마을 유적터에 55년이 지난 오늘에야 온 도민들의 마음을 모아 해원상생의 굿판을 벌여 이를 위무하고, 이곳에 옛 조상들이 그랬듯이 다시는 이러한 일이 발생하지 않기를 기원하며 이 '거욱대'를 세운다.", source: "4·3 해원 상생 거욱대 비문 (2004.4.5)" }
      ],
      REFUSE_KEYWORDS: ["실명", "이름을", "이름이 뭐", "이름은", "성함", "누구였", "주정공장"],
      FALLBACK: "기록에 명시되지 않은 내용입니다."
    },
    en: {
      KB: [
        {
          qa_id: "kb-01",
          question: "What kind of place is Goneul-dong?",
          answer: "It was an old village over 700 years old on the coast of Hwabuk-dong, Jeju City. After it was burned down during 4·3 and never rebuilt, it came to be called 'the lost village.'",
          source: "Survey report · Goneul-dong monument"
        },
        {
          qa_id: "kb-02",
          question: "What happened at Goneul-dong?",
          answer: "Over two days, January 4 and 5, 1949, suppression forces surrounded the village, killed residents, and burned the entire village down. At least around 10 people died (the monument records a different number: 24).",
          source: "Lost Village information board · Goneul-dong monument"
        },
        {
          qa_id: "kb-03",
          question: "How many households were in the village?",
          answer: "The Lost Village information board records 67 households (22 in Angoneul + 17 in Gaundegoneul + 28 in Batgoneul), while the Goneul-dong monument records 43 — the records differ.",
          source: "Lost Village information board · Goneul-dong monument"
        },
        {
          qa_id: "kb-04",
          question: "What remains at Goneul-dong today?",
          answer: "House foundations and 'olle' (small paths connecting houses and village roads) remain, along with the 'Lost Village' information board, the Goneul-dong monument (2003), and the '4·3 Reconciliation Stone Tower' built in 2004.",
          source: "Survey report · on-site information boards"
        }
      ],
      FACTS: [
        { id: "f-01", text: "The former site of Goneul-dong (the Lost Village) is located around lot 4440, Hwabuk 1-dong, Jeju City.", source: "Survey report", hint: "Where is the former site of Goneul-dong?" },
        { id: "f-02", text: "Goneul-dong's coordinates are 33.521722°N, 126.557375°E.", source: "Survey report, field records", hint: "What are Goneul-dong's exact coordinates?" },
        { id: "f-03", text: "Goneul-dong is a 'lost village' destroyed during 4·3 and never rebuilt. House foundations and other traces remain relatively well preserved, and there is a 'Lost Village' information board, a '4·3 Reconciliation Stone Tower' (2004), and an English-language information board.", source: "Survey report", hint: "What does Goneul-dong look like today?" },
        { id: "f-04", text: "Before 4·3, Goneul-dong consisted of three small clusters separated by two branches of the Hwabuk Stream: Angoneul (22 households), Gaundegoneul (17 households), and Batgoneul (28 households).", source: "Lost Village information board · survey report", hint: "What was the village like before 4·3?" },
        { id: "f-05", text: "Around 3-4 p.m. on January 4, 1949, one platoon from the 2nd Regiment of the National Defense Constabulary surrounded Goneul-dong, gathered the villagers, took about 10 young men to the coast and killed them, and burned down all the houses in Angoneul and Gaundegoneul.", source: "Lost Village information board · survey report", hint: "What happened on January 4, 1949?" },
        { id: "f-06", text: "On January 5, 1949, some villagers who had been detained at nearby Hwabuk Elementary School were killed at a coastal spot called 'Yeondimit,' and the houses of Batgoneul were also burned down. After that, Goneul-dong was deserted.", source: "Lost Village information board · survey report", hint: "What happened on January 5, 1949?" },
        { id: "f-07", text: "Over two days, suppression forces killed at least around 10 residents and burned the entire village, which was never rebuilt and became known as 'the lost village.'", source: "Survey report", hint: "What became of the village afterward?" },
        { id: "f-08", text: "On April 5, 2004, the Jeju branch of the Korean National Federation of Artistic and Cultural Organizations erected the '4·3 Reconciliation Stone Tower' to remember the village.", source: "On-site information board (Stone Tower inscription)", hint: "Who built the Stone Tower, and why?" },
        { id: "f-09", text: "On April 3, 2003, the chair of the Jeju 4·3 Truth-Finding and Victim Honor Restoration Task Force and the Governor of Jeju erected the Goneul-dong monument. The monument also notes that Goneul Village dates back over 700 years, with records showing it belonged to Byeoldo-hyeon in 1300, during King Chungnyeol's reign of Goryeo.", source: "On-site information board (Goneul-dong monument)", hint: "What does the Goneul-dong monument say?" },
        { id: "f-10", text: "Olle Trail Course 18 passes through the former site of Goneul-dong; its guide notes, 'You pass through Goneul-dong, a village completely burned down and lost in a scorched-earth operation.' Gwandeokjeong, the spark of 4·3, is also on the same course.", source: "Olle Trail × 4·3 heritage site course guide", hint: "How is Goneul-dong connected to the Olle trail?" },
        { id: "f-11", text: "On February 27, 1949, the 2nd Regiment carried out the execution of 39 people sentenced to death by military tribunal in Hwabuk-ri. The exact location of the execution is not specified in the record.", source: "Jeju 4·3 Incident Chronicle", hint: "Did anything else happen in Hwabuk-ri?" }
      ],
      QUOTES: [
        { id: "q-01", text: "Suppression forces carried out a mass shooting of Goneul-dong residents in Hwabuk-ri, Jeju town, over two days.", source: "Jeju 4·3 Incident Chronicle (1949-01-04) [translated]" },
        { id: "q-02", text: "Goneul-dong was a village on the west coast of Hwabuk 1-dong, Jeju City.", source: "Lost Village (Goneul-dong) information board [translated]" },
        { id: "q-03", text: "Houses and people are gone, leaving only stone walls to remember this unjust and sorrowful history at the ruins of Goneul-dong, scorched fifty-five years ago. Today the people of this island gather their hearts to hold this rite of reconciliation, and we erect this 'stone tower' in hope that such a tragedy will never happen again, as our ancestors once wished.", source: "4·3 Reconciliation Stone Tower inscription (2004.4.5) [translated]" }
      ],
      REFUSE_KEYWORDS: ["real name", "full name", "victim's name", "victims' names", "who were the victims", "name of the victim", "jujeong factory", "liquor factory"],
      FALLBACK: "This is not specified in the record."
    }
  };

  var CHROME = {
    ko: {
      launcherLabel: "제주 4·3 안내 챗봇 열기",
      header: "제주 4·3 안내원",
      placeholder: "곤을동에 대해 물어보세요",
      send: "전송",
      intro: "이런 질문을 해보실 수 있어요:",
      related: "관련 질문:",
      you: "나",
      bot: "안내원",
      sourcePrefix: "출처"
    },
    en: {
      launcherLabel: "Open the Jeju 4·3 guide chatbot",
      header: "Jeju 4·3 Guide",
      placeholder: "Ask about Goneul-dong",
      send: "Send",
      intro: "Try one of these:",
      related: "You might also ask:",
      you: "You",
      bot: "Guide",
      sourcePrefix: "Source"
    }
  };

  function getLang() { return document.documentElement.lang === "en" ? "en" : "ko"; }
  function data() { return DATA[getLang()]; }

  // 흔한 의문사·서술형 어미("무슨", "~있었나요", "what", "did" 등)는 어느 질문에나 등장해
  // 변별력을 흐리므로 통째로 제거하고, 한국어 조사(은/는/이/가/을/를 등)는 단어 끝에서 한 번만
  // 떼어내 핵심 단어만 남긴다.
  var STOP_WORDS = [
    "무슨", "어떻게", "무엇", "왜", "언제", "어디", "누가", "어느", "있었나요", "있나요", "했나요", "됐나요", "됐어요", "인가요",
    "what", "who", "when", "where", "why", "how", "did", "does", "is", "was", "were", "the", "a", "an", "at", "in", "on", "to", "of"
  ];
  var PARTICLE_SUFFIXES = ["에서는", "에게서", "으로는", "이라는", "에서", "이라", "이에요", "했나요", "됐나요", "있나요", "일까요", "까요", "나요", "가요", "이나", "이며", "와", "과", "은", "는", "이", "가", "을", "를", "의", "도", "로"];
  function stripParticle(word) {
    for (var i = 0; i < PARTICLE_SUFFIXES.length; i++) {
      var suf = PARTICLE_SUFFIXES[i];
      if (word.length > suf.length && word.slice(-suf.length) === suf) return word.slice(0, -suf.length);
    }
    return word;
  }
  function normalize(text) {
    var words = (text || "").trim().split(/\s+/).filter(Boolean);
    words = words.filter(function (w) { return STOP_WORDS.indexOf(w.toLowerCase()) === -1; });
    words = words.map(stripParticle);
    return words.join("").toLowerCase();
  }

  function matchesRefuseKeyword(question) {
    var n = normalize(question);
    var keywords = data().REFUSE_KEYWORDS;
    for (var i = 0; i < keywords.length; i++) {
      if (n.indexOf(normalize(keywords[i])) !== -1) return true;
    }
    return false;
  }

  // haystack(h)과 질문(q) 중 더 짧은 쪽의 3글자 조각을 긴 쪽에서 찾는다 — 2글자(바이그램)는
  // "~있었나요" 같은 흔한 어미에도 걸려 변별력이 낮으므로 3글자로 올렸다. 이렇게 하면 KB의 짧은
  // 질문뿐 아니라 FACTS의 길고 상세한 문장을 상대로도 점수가 문장 길이에 좌우되지 않는다.
  function scoreEntry(haystackText, question) {
    var q = normalize(question);
    var h = normalize(haystackText);
    if (!h || !q) return 0;
    // 완전 포함은 아주 강한 신호라 부분 겹침 누적 점수가 절대 못 이기게 확실히 높은 값을 준다
    // (예: 긴 문장은 우연한 3글자 겹침이 많이 쌓여 완전 일치보다 점수가 커질 수 있었음)
    if (h.length >= 2 && (q.indexOf(h) !== -1 || h.indexOf(q) !== -1)) return 20; // 한쪽이 다른 쪽에 완전히 포함
    var shortStr = h.length <= q.length ? h : q;
    var longStr = h.length <= q.length ? q : h;
    var score = 0;
    var N = 3;
    if (shortStr.length >= N) {
      for (var j = 0; j <= shortStr.length - N; j++) {
        if (longStr.indexOf(shortStr.substring(j, j + N)) !== -1) score += 0.5; // 부분 겹침
      }
    }
    return score;
  }

  function bestMatch(question, entries, getHaystacks) {
    var best = null;
    var bestScore = 0;
    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i];
      var haystacks = getHaystacks(entry);
      var s = 0;
      for (var j = 0; j < haystacks.length; j++) {
        s = Math.max(s, scoreEntry(haystacks[j], question));
      }
      if (s > bestScore) {
        bestScore = s;
        best = entry;
      }
    }
    return { entry: best, score: bestScore };
  }

  // 카드 내용 전체(KB 추천 질문 + FACTS 검증 사실 + QUOTES 원문 인용)를 근거로 답한다.
  // 세 후보군의 점수를 함께 비교해 실제로 가장 관련 있는 답을 고른다 — KB를 무조건 먼저
  // 확정해버리면 KB 질문 문구와 어투만 비슷한 다른 주제 질문에도 KB가 잘못 뽑힐 수 있다.
  // 점수 계산은 entry.question·entry.answer(또는 text) 문장 자체로만 비교한다.
  function answer(question) {
    var d = data();
    if (!question || !question.trim()) {
      return { text: d.FALLBACK, source: null };
    }
    if (matchesRefuseKeyword(question)) {
      return { text: d.FALLBACK, source: null };
    }

    var kbMatch = bestMatch(question, d.KB, function (e) { return [e.question, e.answer]; });
    var factMatch = bestMatch(question, d.FACTS, function (e) { return [e.text]; });
    var quoteMatch = bestMatch(question, d.QUOTES, function (e) { return [e.text]; });

    var candidates = [
      { score: kbMatch.score, text: kbMatch.entry && kbMatch.entry.answer, source: kbMatch.entry && kbMatch.entry.source, id: kbMatch.entry && kbMatch.entry.qa_id, priority: 0 },
      { score: factMatch.score, text: factMatch.entry && factMatch.entry.text, source: factMatch.entry && factMatch.entry.source, id: factMatch.entry && factMatch.entry.id, priority: 1 },
      { score: quoteMatch.score, text: quoteMatch.entry && quoteMatch.entry.text, source: quoteMatch.entry && quoteMatch.entry.source, id: quoteMatch.entry && quoteMatch.entry.id, priority: 2 }
    ].filter(function (c) { return c.text; });
    candidates.sort(function (a, b) { return (b.score - a.score) || (a.priority - b.priority); });

    var top = candidates[0];
    if (top && top.score >= 1) {
      return { text: top.text, source: top.source, id: top.id };
    }
    return { text: d.FALLBACK, source: null, id: null };
  }

  // 답변이 KB든 FACTS든 상관없이, "자연스러운 질문 문구"가 있는 항목만 관련 질문 후보로 쓴다
  // (KB는 question, FACTS는 hint). QUOTES는 원문 인용이라 질문형 문구가 없어 후보에서 뺀다.
  function followupPool() {
    var d = data();
    var pool = d.KB.map(function (e) { return { id: e.qa_id, question: e.question }; });
    pool = pool.concat(d.FACTS.map(function (e) { return { id: e.id, question: e.hint }; }));
    return pool;
  }

  // 우측 하단 launcher가 눈에 띄도록 완만한 부유(float) + 은은한 펄스 애니메이션을 부여한다.
  function injectAnimStyle() {
    if (document.getElementById("chatbot-anim-style")) return;
    var style = document.createElement("style");
    style.id = "chatbot-anim-style";
    style.textContent =
      "@keyframes chatbotFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}" +
      "@keyframes chatbotPulse{0%{box-shadow:0 2px 8px rgba(0,0,0,0.25),0 0 0 0 rgba(224,96,122,0.45)}" +
      "70%{box-shadow:0 2px 8px rgba(0,0,0,0.25),0 0 0 14px rgba(224,96,122,0)}" +
      "100%{box-shadow:0 2px 8px rgba(0,0,0,0.25),0 0 0 0 rgba(224,96,122,0)}}" +
      "#chatbot-launcher{animation:chatbotFloat 2.6s ease-in-out infinite, chatbotPulse 2.6s ease-out infinite;}" +
      "#chatbot-launcher:hover{animation-play-state:paused;}";
    document.head.appendChild(style);
  }

  function buildWidget() {
    injectAnimStyle();

    var chrome = CHROME[getLang()];

    var launcher = document.createElement("button");
    launcher.id = "chatbot-launcher";
    launcher.type = "button";
    launcher.setAttribute("aria-label", chrome.launcherLabel);
    // 동백꽃(제주 4·3 추모 상징) 캐릭터 아이콘 — 말풍선 이모지 대신, 아이들에게도 친근하고
    // 실제 4·3 추모 문화(동백꽃, 다시 피어나라)와 맞닿아 있는 모티프로 교체
    launcher.innerHTML =
      '<svg viewBox="0 0 100 100" width="34" height="34" aria-hidden="true">' +
      '<g>' +
      '<ellipse cx="50" cy="20" rx="16" ry="22" fill="#e0607a"/>' +
      '<ellipse cx="50" cy="20" rx="16" ry="22" fill="#e0607a" transform="rotate(60 50 50)"/>' +
      '<ellipse cx="50" cy="20" rx="16" ry="22" fill="#e0607a" transform="rotate(120 50 50)"/>' +
      '<ellipse cx="50" cy="20" rx="16" ry="22" fill="#e0607a" transform="rotate(180 50 50)"/>' +
      '<ellipse cx="50" cy="20" rx="16" ry="22" fill="#e0607a" transform="rotate(240 50 50)"/>' +
      '<ellipse cx="50" cy="20" rx="16" ry="22" fill="#e0607a" transform="rotate(300 50 50)"/>' +
      '<circle cx="50" cy="50" r="16" fill="#f6c94d"/>' +
      '<circle cx="44" cy="48" r="2.2" fill="#3a2f2a"/>' +
      '<circle cx="56" cy="48" r="2.2" fill="#3a2f2a"/>' +
      '<path d="M44 55 Q50 60 56 55" stroke="#3a2f2a" stroke-width="2" fill="none" stroke-linecap="round"/>' +
      '</g></svg>';
    launcher.style.cssText =
      "position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;" +
      "background:#fff7f2;color:#fff;border:none;cursor:pointer;" +
      "display:flex;align-items:center;justify-content:center;" +
      "box-shadow:0 2px 8px rgba(0,0,0,0.25);z-index:9999;";

    // 05-assemble이 정적으로 심어둔 <div id="chatbot-modal" data-kb-source="07"> 컨테이너를
    // 그대로 찾아서 채운다 (05가 마크업을 안 심어뒀을 경우에만 새로 만든다 — 방어적 처리).
    var modal = document.getElementById("chatbot-modal");
    var modalWasStatic = !!modal;
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "chatbot-modal";
      modal.setAttribute("data-kb-source", "07");
    }
    modal.style.cssText =
      "position:fixed;right:20px;bottom:88px;width:320px;max-height:420px;display:none;" +
      "flex-direction:column;background:#fff;border:1px solid #D3D1C7;border-radius:12px;" +
      "box-shadow:0 4px 16px rgba(0,0,0,0.2);z-index:9999;overflow:hidden;font-family:sans-serif;";

    var header = document.createElement("div");
    header.textContent = chrome.header;
    header.style.cssText = "padding:10px 12px;background:#93381f;color:#fff;font-size:14px;";

    var log = document.createElement("div");
    log.id = "chatbot-log";
    log.style.cssText = "flex:1;overflow-y:auto;padding:10px;font-size:13px;color:#2C2C2A;";

    var suggestionsBox = document.createElement("div");
    log.appendChild(suggestionsBox);

    var inputRow = document.createElement("div");
    inputRow.style.cssText = "display:flex;border-top:1px solid #D3D1C7;";

    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = chrome.placeholder;
    input.style.cssText = "flex:1;border:none;padding:8px;font-size:13px;outline:none;";

    var sendBtn = document.createElement("button");
    sendBtn.type = "button";
    sendBtn.textContent = chrome.send;
    sendBtn.style.cssText = "border:none;background:#93381f;color:#fff;padding:0 12px;cursor:pointer;";

    // who==="bot"일 때는 한 글자씩 타이핑되는 효과로 보여준다. 사용자 입력은 textContent로만
    // 다뤄서 사용자가 태그를 입력해도 그대로 문자로만 표시된다(innerHTML에 직접 넣지 않음).
    // onDone은 타이핑이 다 끝난 뒤(봇 메시지에만) 한 번 호출된다 — 관련 질문 칩을 그때 붙인다.
    function appendMessage(text, who, sourceHtml, onDone) {
      var c = CHROME[getLang()];
      var msg = document.createElement("div");
      msg.style.cssText = "margin-bottom:8px;";
      var label = document.createElement("strong");
      label.style.color = who === "user" ? "#854F0B" : "#93381f";
      label.textContent = (who === "user" ? c.you : c.bot) + ": ";
      var body = document.createElement("span");
      msg.appendChild(label);
      msg.appendChild(body);
      log.appendChild(msg);
      log.scrollTop = log.scrollHeight;

      if (who !== "bot") {
        body.textContent = text;
        log.scrollTop = log.scrollHeight;
        return;
      }

      var i = 0;
      var timer = setInterval(function () {
        i++;
        body.textContent = text.slice(0, i);
        log.scrollTop = log.scrollHeight;
        if (i >= text.length) {
          clearInterval(timer);
          if (sourceHtml) msg.insertAdjacentHTML("beforeend", sourceHtml);
          log.scrollTop = log.scrollHeight;
          if (onDone) onDone(msg);
        }
      }, 22);
    }

    // 이미 물어본(또는 답으로 나온) 항목은 다시 추천하지 않는다 — 페이지를 새로고침하면 초기화됨.
    var shownIds = {};

    function renderFollowups(container) {
      var c = CHROME[getLang()];
      var candidates = followupPool().filter(function (e) { return e.question && !shownIds[e.id]; });
      if (!candidates.length) return;
      // 무작위로 최대 2개 — 매번 같은 순서로 추천되지 않게
      candidates.sort(function () { return Math.random() - 0.5; });
      var picks = candidates.slice(0, 2);

      var wrap = document.createElement("div");
      wrap.style.cssText = "margin-top:8px;";
      var label = document.createElement("div");
      label.style.cssText = "font-size:11px;color:#8a8a86;margin-bottom:4px;";
      label.textContent = c.related;
      wrap.appendChild(label);

      var chipsWrap = document.createElement("div");
      chipsWrap.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;";
      picks.forEach(function (item) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.textContent = item.question;
        chip.style.cssText =
          "border:1px solid #c1502e;background:#fff;color:#93381f;border-radius:14px;" +
          "padding:6px 10px;font-size:12px;cursor:pointer;text-align:left;";
        chip.addEventListener("click", function () { handleSend(item.question); });
        chipsWrap.appendChild(chip);
      });
      wrap.appendChild(chipsWrap);
      container.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
    }

    function handleSend(overrideText) {
      var q = overrideText !== undefined ? overrideText : input.value;
      if (!q.trim()) return;
      appendMessage(q, "user");
      input.value = "";
      var result = answer(q);
      if (result.id) shownIds[result.id] = true;
      var c = CHROME[getLang()];
      var sourceHtml = result.source
        ? ' <span style="color:#8a8a86;font-size:11px;">(' + c.sourcePrefix + ": " + result.source + ")</span>"
        : "";
      appendMessage(result.text, "bot", sourceHtml, result.id ? renderFollowups : null);
    }

    // KB에 실제로 있는 질문만 추천 칩으로 보여준다(없는 질문을 지어내지 않음).
    // 언어가 바뀌면 다시 불러 칩 문구도 그 언어로 갈아 끼운다.
    function renderSuggestions() {
      var c = CHROME[getLang()];
      suggestionsBox.innerHTML = "";

      var intro = document.createElement("div");
      intro.style.cssText = "margin-bottom:8px;color:#6b6255;";
      intro.textContent = c.intro;
      suggestionsBox.appendChild(intro);

      var chipsWrap = document.createElement("div");
      chipsWrap.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;";
      data().KB.forEach(function (entry) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.textContent = entry.question;
        chip.style.cssText =
          "border:1px solid #c1502e;background:#fff;color:#93381f;border-radius:14px;" +
          "padding:6px 10px;font-size:12px;cursor:pointer;text-align:left;";
        chip.addEventListener("click", function () { handleSend(entry.question); });
        chipsWrap.appendChild(chip);
      });
      suggestionsBox.appendChild(chipsWrap);
    }

    renderSuggestions();

    sendBtn.addEventListener("click", function () { handleSend(); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") handleSend();
    });

    launcher.addEventListener("click", function () {
      modal.style.display = modal.style.display === "none" ? "flex" : "none";
    });

    // 메인 화면 언어 토글이 바뀌면(index.html의 setLang, 또는 이 페이지 자체의 lang 동기화)
    // 위젯 화면 문구·추천 칩·답변 언어를 모두 함께 갱신한다.
    window.addEventListener("jeju43:langchange", function () {
      var c = CHROME[getLang()];
      launcher.setAttribute("aria-label", c.launcherLabel);
      header.textContent = c.header;
      input.placeholder = c.placeholder;
      sendBtn.textContent = c.send;
      renderSuggestions();
    });

    inputRow.appendChild(input);
    inputRow.appendChild(sendBtn);
    modal.appendChild(header);
    modal.appendChild(log);
    modal.appendChild(inputRow);

    document.body.appendChild(launcher);
    if (!modalWasStatic) document.body.appendChild(modal);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildWidget);
  } else {
    buildWidget();
  }
})();
