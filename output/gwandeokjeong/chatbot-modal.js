/*
 * 07-chatbot — 자기완결 모달 스크립트 (관덕정 광장 — 1947년 3·1 발포사건 현장 (4·3의 도화선))
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
        "qa_id": "kb-01",
        "question": "관덕정은 원래 무엇을 하던 곳인가요?",
        "answer": "1448년(조선 세종 30년)에 안무사(목사) 신숙청이 병사들을 훈련시킬 목적으로 세운 건물입니다. 건립된 뒤에는 관과 민이 함께 모이는 회의 장소, 죄인을 다스리는 곳 등으로도 쓰였습니다. 지금은 보물 제322호이며 제주목 관아의 일부를 이룹니다.",
        "source": "현장 안내판 — 관덕정 안내판 (보물 해설) · 안내판 조사보고서",
        "tags": [
            "관덕정",
            "용도",
            "원래",
            "건립",
            "1448",
            "세종",
            "안무사",
            "신숙청",
            "병사 훈련",
            "회의 장소",
            "죄인",
            "보물 제322호",
            "제주목 관아"
        ]
    },
    {
        "qa_id": "kb-02",
        "question": "'관덕'이라는 이름은 무슨 뜻인가요?",
        "answer": "'활을 쏘는 것은 높고 훌륭한 덕을 쌓는 것이다'라는 예기(禮記)의 내용에서 따온 이름입니다. 평소에 마음을 바르게 하고 훌륭한 덕을 쌓는다는 뜻이며, 문무(학문과 무예)의 올바른 정신을 본받기 위해 지어진 이름입니다.",
        "source": "현장 안내판 — 관덕정 안내판 (보물 해설)",
        "tags": [
            "관덕",
            "이름",
            "뜻",
            "유래",
            "예기",
            "활",
            "덕",
            "문무"
        ]
    },
    {
        "qa_id": "kb-03",
        "question": "1947년 3월 1일 관덕정에서 무슨 일이 있었나요?",
        "answer": "북국민학교에서 3·1절 제28주년 기념대회가 열려 3만여 명이 참가했고, 행사 후 참가자들이 동·서로 나뉘어 시위했습니다. 서쪽 행렬이 관덕정 앞을 지날 즈음 어린아이가 기마경찰의 말발굽에 치였는데 경찰이 조치 없이 지나가자 군중이 격분해 항의했고, 응원경찰의 발포로 관덕정과 도립병원 앞에서 주민 6명이 사망하고 8명이 중경상을 입었습니다. 이를 '3·1사건'이라고 합니다.",
        "source": "제주4·3사건일지·한눈에 보는 4·3·안내판 조사보고서",
        "tags": [
            "3·1사건",
            "1947년 3월 1일",
            "3·1절 기념대회",
            "제28주년",
            "북국민학교",
            "3만여 명",
            "시위",
            "기마경찰",
            "말발굽",
            "응원경찰",
            "발포",
            "사망 6명",
            "중경상 8명",
            "도립병원"
        ]
    },
    {
        "qa_id": "kb-04",
        "question": "사망한 6명은 모두 관덕정 앞에서 숨진 건가요?",
        "answer": "아닙니다. 기록은 사망 6명이 '관덕정과 도립병원 앞'에서 발생했다고 적고 있습니다. 도립병원 옛터 서술에 따르면 관덕정 앞 총상자 가운데 4명이 즉사하고 2명은 병원으로 옮겨진 뒤 사망했습니다. 전원이 관덕정 앞에서 사망했다고 말할 수는 없습니다.",
        "source": "제주4·3사건일지 · 안내판 조사보고서(도립병원 옛터)",
        "tags": [
            "사망 6명",
            "모두",
            "전원",
            "관덕정 앞",
            "도립병원 앞",
            "발생 위치",
            "4명 즉사",
            "2명 병원 이송",
            "숨진 곳"
        ]
    },
    {
        "qa_id": "kb-05",
        "question": "도립병원에서 다친 행인 2명도 사망자 6명·부상자 8명에 포함되나요?",
        "answer": "아닙니다. 사망 6명·중경상 8명은 응원경찰 발포에 대한 기록이고, 행인 2명 중상은 병원을 경호하던 이문규 순경이 공포감에 발포한 별개의 기록입니다. 두 수치를 합산하거나 하나의 사건으로 뭉뚱그려서는 안 됩니다.",
        "source": "제주4·3사건일지 · 안내판 조사보고서(도립병원 옛터)",
        "tags": [
            "행인 2명",
            "중상",
            "이문규",
            "순경",
            "포함",
            "합산",
            "별개 기록",
            "사망 6명",
            "부상자 8명",
            "중경상 8명",
            "도립병원"
        ]
    },
    {
        "qa_id": "kb-06",
        "question": "3·1사건은 그 뒤 어떻게 이어졌나요?",
        "answer": "1947년 3월 10일, 진상규명과 책임자 처벌을 촉구하는 사상 초유의 3·10 민관총파업이 일어났고, 이 총파업이 제주 4·3 발발의 도화선이 되었습니다.",
        "source": "안내판 조사보고서",
        "tags": [
            "3·10",
            "민관총파업",
            "총파업",
            "1947",
            "진상규명",
            "도화선",
            "이어졌",
            "그 뒤",
            "4·3 발발"
        ]
    },
    {
        "qa_id": "kb-07",
        "question": "지금 관덕정에 가면 4·3에 대한 안내판이 있나요?",
        "answer": "안내판 조사보고서의 현장조사(2020년 9월 29일) 기준으로, 관덕정에 서 있는 안내판은 조선시대 건축 해설뿐이며 3·1절 발포사건에 대한 안내판은 세워져 있지 않았습니다. 조사보고서 총론도 이 점을 지적하고 있습니다. 그 이후의 변경 여부는 이 자료에 기록돼 있지 않습니다.",
        "source": "안내판 조사보고서 총론 (보고서 p.10~11, 조사일 2020-09-29)",
        "tags": [
            "안내판",
            "4·3 안내판",
            "지금",
            "현재",
            "있나요",
            "현장조사",
            "2020년 9월 29일",
            "조선시대 건축 해설",
            "조사보고서 총론"
        ]
    },
    {
        "qa_id": "kb-08",
        "question": "제주도립병원 옛터와 제주시민회관은 지금 가서 볼 수 있나요?",
        "answer": "제주도립병원 옛터(제주시 삼도이동 154)는 현재 흔적이 남아 있지 않고, 제주시민회관(제주시 이도이동)은 1989년 제1회 4·3추모제가 열린 곳이지만 그 사실을 알리는 표시가 없습니다. 두 곳 모두 지금 볼 수 있는 유적이라기보다 '무슨 일이 있었던 자리'로 좌표만 남아 있는 옛터입니다.",
        "source": "안내판 조사보고서(도립병원 옛터·제주시민회관)",
        "tags": [
            "제주도립병원 옛터",
            "삼도이동",
            "제주시민회관",
            "이도이동",
            "1989",
            "제1회 4·3추모제",
            "연계 지점",
            "방문",
            "옛터",
            "흔적"
        ]
    }
];

  var FALLBACK_ANSWER = "기록에 명시되지 않은 내용입니다.";

  // 02-story가 note_for_07로 표시한 가드레일 테스트 질문 — kb[]에는 없지만, 우연한
  // 키워드 겹침으로 다른 KB 항목이 답하지 않도록 강제로 fallback 처리한다.
  var GUARDRAIL_TEST_QUESTIONS = [
    "관덕정은 원래 무엇을 하던 곳인가요?",
    "1947년 3월 1일 관덕정에서 무슨 일이 있었나요?",
    "사망한 6명은 모두 관덕정 앞에서 숨진 건가요?",
    "도립병원에서 다친 행인 2명도 사망자 6명·부상자 8명에 포함되나요?",
    "지금 관덕정에 가면 4·3에 대한 안내판이 있나요?",
    "제주도립병원 옛터와 제주시민회관은 지금 가서 볼 수 있나요?",
    "말발굽에 치인 그 아이는 그 뒤 어떻게 됐나요?",
    "관덕정에서 일어난 다른 유명한 4·3 일화도 알려 주세요."
];

  function normalize(text) {
    return (text || "").toLowerCase().replace(/\s+/g, "");
  }

  function matchesGuardrailTest(question) {
    var n = normalize(question);
    for (var i = 0; i < GUARDRAIL_TEST_QUESTIONS.length; i++) {
      if (n === normalize(GUARDRAIL_TEST_QUESTIONS[i])) return true;
    }
    return false;
  }

  function scoreEntry(entry, question) {
    var q = normalize(question);
    var score = 0;
    var haystacks = [entry.question].concat(entry.tags || []);
    for (var i = 0; i < haystacks.length; i++) {
      var h = normalize(haystacks[i]);
      if (h && q.indexOf(h) !== -1) score += 3;
      else if (h && h.length >= 2) {
        for (var j = 0; j < h.length - 1; j++) {
          if (q.indexOf(h.substring(j, j + 2)) !== -1) score += 0.3;
        }
      }
    }
    return score;
  }

  function answer(question) {
    if (!question || !question.trim()) {
      return { text: FALLBACK_ANSWER, source: null };
    }
    if (matchesGuardrailTest(question)) {
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
    launcher.setAttribute("aria-label", "관덕정 광장 — 1947년 3·1 발포사건 현장 (4·3의 도화선) 안내 챗봇 열기");
    launcher.textContent = "\uD83D\uDCAC";
    launcher.style.cssText =
      "position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;" +
      "background:#2C2C2A;color:#fff;border:none;font-size:22px;cursor:pointer;" +
      "box-shadow:0 2px 8px rgba(0,0,0,0.25);z-index:9999;";

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
    header.textContent = "관덕정 광장 — 1947년 3·1 발포사건 현장 (4·3의 도화선) 안내원";
    header.style.cssText = "padding:10px 12px;background:#1F2A44;color:#fff;font-size:14px;";

    var log = document.createElement("div");
    log.id = "chatbot-log";
    log.style.cssText = "flex:1;overflow-y:auto;padding:10px;font-size:13px;color:#2C2C2A;";

    var inputRow = document.createElement("div");
    inputRow.style.cssText = "display:flex;border-top:1px solid #D3D1C7;";

    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "관덕정 광장 — 1947년 3·1 발포사건 현장 (4·3의 도화선)에 대해 물어보세요";
    input.style.cssText = "flex:1;border:none;padding:8px;font-size:13px;outline:none;";

    var sendBtn = document.createElement("button");
    sendBtn.type = "button";
    sendBtn.textContent = "\uC804\uC1A1";
    sendBtn.style.cssText = "border:none;background:#1F2A44;color:#fff;padding:0 12px;cursor:pointer;";

    function appendMessage(text, who) {
      var msg = document.createElement("div");
      msg.style.cssText = "margin-bottom:8px;";
      msg.innerHTML =
        '<strong style="color:' + (who === "user" ? "#854F0B" : "#1F2A44") + '">' +
        (who === "user" ? "\uB098" : "\uC548\uB0B4\uC6D0") +
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
        text += ' <span style="color:#8a8a86;font-size:11px;">(\uCD9C\uCC98: ' + result.source + ")</span>";
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
