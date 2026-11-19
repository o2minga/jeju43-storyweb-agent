/*
 * 07-chatbot — 자기완결 모달 스크립트 (gwandeokjeong)
 * 05-assemble은 이 파일을 <script src="chatbot-modal.js"></script>로 삽입만 하면 된다.
 * KB/가드레일 데이터는 이 파일 안에 내장되어 있어 별도 fetch가 필요 없다.
 *
 * 한계: 이 매칭은 클라이언트 사이드 키워드 스코어링이다 — 실제 LLM 기반 RAG가 아니라
 * 07 스킬이 정의한 KB/가드레일 규칙을 정적 사이트에서도 동작하게 구현한 간이 버전이다.
 */
(function () {
  "use strict";

  var KB = [
    {
      qa_id: "kb-01",
      question: "관덕정은 원래 무엇을 하던 곳인가요?",
      answer: "조선시대인 1448년, 병사들을 훈련시키기 위해 세워진 건물로, 이후 관과 백성이 모이는 회의 장소로도 쓰였습니다.",
      source: "현장 안내판",
      tags: ["관덕정", "용도", "건립", "1448", "회의장소", "훈련"]
    },
    {
      qa_id: "kb-02",
      question: "관덕정에서 무슨 일이 있었나요?",
      answer: "1947년 3월 1일, 3·1절 기념대회 후 시위 중 경찰의 발포로 관덕정과 인근 도립병원 앞에서 주민 6명이 숨지고 8명이 다쳤습니다. 이 사건은 이후 4·3의 도화선이 된 3·10 민관총파업으로 이어졌습니다.",
      source: "제주4·3사건일지·안내판 조사보고서",
      tags: ["3·1사건", "발포", "1947", "4·3", "도화선", "3·10", "민관총파업"]
    }
  ];

  var FALLBACK_ANSWER = "기록에 명시되지 않은 내용입니다.";

  // forbidden_topics(01-verify)에서 뽑은 거절 트리거 키워드 — 휴리스틱이다.
  // 실제 서비스에서는 이 판정을 LLM 가드레일 프롬프트가 대신하는 것이 정석이며,
  // 이 목록은 정적 페이지에서 최소한의 안전망 역할만 한다.
  var REFUSE_KEYWORDS = [
    "생사", "죽었", "살았", "어떻게 됐", "어떻게됐",
    "무장대 지도자", "시신 전시", "지도자 시신"
  ];

  function normalize(text) {
    return (text || "").toLowerCase().replace(/\s+/g, "");
  }

  function matchesRefuseKeyword(question) {
    var n = normalize(question);
    for (var i = 0; i < REFUSE_KEYWORDS.length; i++) {
      if (n.indexOf(normalize(REFUSE_KEYWORDS[i])) !== -1) return true;
    }
    return false;
  }

  function scoreEntry(entry, question) {
    var q = normalize(question);
    var score = 0;
    var haystacks = [entry.question].concat(entry.tags || []);
    for (var i = 0; i < haystacks.length; i++) {
      var h = normalize(haystacks[i]);
      if (h && q.indexOf(h) !== -1) score += 3; // 질문/태그 전체가 포함
      else if (h && h.length >= 2) {
        for (var j = 0; j < h.length - 1; j++) {
          if (q.indexOf(h.substring(j, j + 2)) !== -1) score += 0.3; // 부분 겹침
        }
      }
    }
    return score;
  }

  function answer(question) {
    if (!question || !question.trim()) {
      return { text: FALLBACK_ANSWER, source: null };
    }
    if (matchesRefuseKeyword(question)) {
      return { text: FALLBACK_ANSWER, source: null };
    }
    var best = null;
    var bestScore = 0;
    for (var i = 0; i < KB.length; i++) {
      var s = scoreEntry(KB[i], question);
      if (s > bestScore) {
        bestScore = s;
        best = KB[i];
      }
    }
    if (best && bestScore >= 1) {
      return { text: best.answer, source: best.source };
    }
    return { text: FALLBACK_ANSWER, source: null };
  }

  function buildWidget() {
    var launcher = document.createElement("button");
    launcher.id = "chatbot-launcher";
    launcher.type = "button";
    launcher.setAttribute("aria-label", "관덕정 안내 챗봇 열기");
    launcher.textContent = "💬";
    launcher.style.cssText =
      "position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;" +
      "background:#2C2C2A;color:#fff;border:none;font-size:22px;cursor:pointer;" +
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
    header.textContent = "관덕정 안내원";
    header.style.cssText = "padding:10px 12px;background:#1F2A44;color:#fff;font-size:14px;";

    var log = document.createElement("div");
    log.id = "chatbot-log";
    log.style.cssText = "flex:1;overflow-y:auto;padding:10px;font-size:13px;color:#2C2C2A;";

    var inputRow = document.createElement("div");
    inputRow.style.cssText = "display:flex;border-top:1px solid #D3D1C7;";

    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "관덕정에 대해 물어보세요";
    input.style.cssText = "flex:1;border:none;padding:8px;font-size:13px;outline:none;";

    var sendBtn = document.createElement("button");
    sendBtn.type = "button";
    sendBtn.textContent = "전송";
    sendBtn.style.cssText = "border:none;background:#1F2A44;color:#fff;padding:0 12px;cursor:pointer;";

    function appendMessage(text, who) {
      var msg = document.createElement("div");
      msg.style.cssText = "margin-bottom:8px;";
      msg.innerHTML =
        '<strong style="color:' + (who === "user" ? "#854F0B" : "#1F2A44") + '">' +
        (who === "user" ? "나" : "안내원") +
        "</strong>: " +
        text;
      log.appendChild(msg);
      log.scrollTop = log.scrollHeight;
    }

    function handleSend() {
      var q = input.value;
      if (!q.trim()) return;
      appendMessage(q, "user");
      input.value = "";
      var result = answer(q);
      var text = result.text;
      if (result.source) {
        text += ' <span style="color:#8a8a86;font-size:11px;">(출처: ' + result.source + ")</span>";
      }
      appendMessage(text, "bot");
    }

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") handleSend();
    });

    launcher.addEventListener("click", function () {
      modal.style.display = modal.style.display === "none" ? "flex" : "none";
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
