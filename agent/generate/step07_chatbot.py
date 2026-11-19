"""07-chatbot 실제 생성 — Group A(추론형) KB/가드레일 데이터는 Claude 호출로 만들고,
모달 위젯 JS(chatbot-modal.js)는 그 결과를 결정론적 코드로 템플릿화한다(위젯 코드 자체는
LLM이 매번 새로 작성하게 하지 않는다 — 재현성·일관된 UI를 위해).

가드레일 테스트 항목(note_for_07) 필터는 프롬프트 지침(호스트 에이전트에게 "kb[]에
넣지 마라"고 지시)만으로 끝내지 않는다 — 모델이 지침을 놓쳐도 실제 답변 가능 KB에
가드레일 테스트 질문이 새어 들어가지 않도록, generate() 마지막에 코드가 qa_id 기준으로
강제로 한 번 더 걸러낸다(_filter_guardrail_test_entries). 모델은 1차 방어선, 코드가
최종 방어선이다.
"""
from __future__ import annotations

import json
import logging

from agents.chatbot_agent import ChatbotAgent
from schema.step01_verify import Step01VerifyOutput
from schema.step02_story import ChatbotKBEntry, Step02StoryOutput
from schema.step07_chatbot import Step07ChatbotOutput

logger = logging.getLogger("agent.generate.step07_chatbot")


def generate(
    location_id: str,
    step01: Step01VerifyOutput,
    step02: Step02StoryOutput,
    extra_instruction: str | None = None,
) -> Step07ChatbotOutput:
    """extra_instruction: self_repair가 08 검수 fail 항목을 좁게 고쳐 달라고 덧붙이는
    추가 지시(있으면 user_content 맨 끝에 그대로 붙는다). 평소 실행에서는 None."""
    user_content = (
        "아래는 02-story의 chatbot_kb 초안과, 01-verify의 forbidden_topics·conflicts·"
        "precision_guardrails다. SKILL.md의 지시에 따라 07-chatbot 출력을 생성하라.\n"
        "- chatbot_kb에 없는 사실을 KB에 새로 넣지 마라.\n"
        "- note_for_07이 붙은 항목(가드레일 테스트용)은 kb[]에 넣지 말고, 그 질문 유형이 "
        "  fallback으로 처리되도록 guardrail에 반영하라.\n"
        "- forbidden_topics는 요약·순화 없이 그대로 refuse_topics에 반영하라.\n"
        "- chatbot_kb가 비어 있으면 kb: []로 두되 가드레일은 유지하라.\n"
        f'- widget.launcher는 정확히 "floating-bottom-right", widget.modal_script_path는 정확히 '
        f'"output/{location_id}/chatbot-modal.js"로 채워라.\n\n'
        f"## location_id\n{location_id}\n\n"
        f"## 02-story.chatbot_kb\n{json.dumps([e.model_dump() for e in step02.chatbot_kb], ensure_ascii=False, indent=2)}\n\n"
        f"## 01-verify.forbidden_topics\n{json.dumps(step01.forbidden_topics, ensure_ascii=False, indent=2)}\n\n"
        f"## 02-story.conflicts_carried_forward\n{json.dumps([c.model_dump() for c in step02.conflicts_carried_forward], ensure_ascii=False, indent=2)}\n\n"
        f"## 02-story.precision_guardrails_applied\n{json.dumps([g.model_dump() for g in step02.precision_guardrails_applied], ensure_ascii=False, indent=2)}"
    )
    if extra_instruction:
        user_content = f"{user_content}\n\n---\n{extra_instruction}"
    result = ChatbotAgent().run(user_content)
    return _filter_guardrail_test_entries(result, step02.chatbot_kb)


def _filter_guardrail_test_entries(
    result: Step07ChatbotOutput, step02_chatbot_kb: list[ChatbotKBEntry]
) -> Step07ChatbotOutput:
    """02의 chatbot_kb 중 note_for_07이 붙은 항목(가드레일 테스트용)의 qa_id가 호스트
    에이전트의 kb[]에 섞여 있으면 코드로 강제 제거한다. 프롬프트 지침(위 user_content의
    두 번째 규칙)이 1차 방어선이고, 이건 모델이 그 지침을 놓쳤을 때의 최종 방어선이다."""
    test_qa_ids = {e.qa_id for e in step02_chatbot_kb if e.note_for_07}
    if not test_qa_ids:
        return result

    leaked = [entry.qa_id for entry in result.kb if entry.qa_id in test_qa_ids]
    if not leaked:
        return result

    logger.warning(
        "07-chatbot: 가드레일 테스트 항목이 kb[]에 섞여 있어 코드로 강제 제거함: %s",
        leaked,
    )
    filtered_kb = [entry for entry in result.kb if entry.qa_id not in test_qa_ids]
    return result.model_copy(update={"kb": filtered_kb})


def build_chatbot_modal_js(location_name_ko: str, step07: Step07ChatbotOutput, step02_chatbot_kb: list[ChatbotKBEntry]) -> str:
    kb_for_js = [
        {
            "qa_id": e.qa_id,
            "question": e.question.ko,
            "answer": e.answer.ko,
            "source": e.source,
            "tags": e.tags,
        }
        for e in step07.kb
    ]
    # note_for_07이 붙은(가드레일 테스트용으로 kb[]에서 의도적으로 빠진) 질문은, 키워드 점수가
    # 우연히 다른 KB 항목과 겹쳐도 무조건 fallback으로 가도록 별도로 표시해 둔다.
    guardrail_test_questions = [e.question.ko for e in step02_chatbot_kb if e.note_for_07]

    kb_json = json.dumps(kb_for_js, ensure_ascii=False, indent=4)
    test_questions_json = json.dumps(guardrail_test_questions, ensure_ascii=False, indent=4)
    fallback = json.dumps(step07.guardrail.fallback_answer.ko, ensure_ascii=False)
    aria_label = json.dumps(f"{location_name_ko} 안내 챗봇 열기", ensure_ascii=False)
    header_text = json.dumps(f"{location_name_ko} 안내원", ensure_ascii=False)
    placeholder_text = json.dumps(f"{location_name_ko}에 대해 물어보세요", ensure_ascii=False)

    return f"""/*
 * 07-chatbot — 자기완결 모달 스크립트 ({location_name_ko})
 * 05-assemble은 이 파일을 <script src="chatbot-modal.js"></script>로 삽입만 하면 된다.
 * KB/가드레일 데이터는 이 파일 안에 내장되어 있어 별도 fetch가 필요 없다.
 *
 * 한계: 이 매칭은 클라이언트 사이드 키워드 스코어링이다 — 실제 LLM 기반 RAG가 아니라
 * 07 스킬이 정의한 KB/가드레일 규칙을 정적 사이트에서도 동작하게 구현한 간이 버전이다.
 */
(function () {{
  "use strict";

  var KB = {kb_json};

  var FALLBACK_ANSWER = {fallback};

  // 02-story가 note_for_07로 표시한 가드레일 테스트 질문 — kb[]에는 없지만, 우연한
  // 키워드 겹침으로 다른 KB 항목이 답하지 않도록 강제로 fallback 처리한다.
  var GUARDRAIL_TEST_QUESTIONS = {test_questions_json};

  function normalize(text) {{
    return (text || "").toLowerCase().replace(/\\s+/g, "");
  }}

  function matchesGuardrailTest(question) {{
    var n = normalize(question);
    for (var i = 0; i < GUARDRAIL_TEST_QUESTIONS.length; i++) {{
      if (n === normalize(GUARDRAIL_TEST_QUESTIONS[i])) return true;
    }}
    return false;
  }}

  function scoreEntry(entry, question) {{
    var q = normalize(question);
    var score = 0;
    var haystacks = [entry.question].concat(entry.tags || []);
    for (var i = 0; i < haystacks.length; i++) {{
      var h = normalize(haystacks[i]);
      if (h && q.indexOf(h) !== -1) score += 3;
      else if (h && h.length >= 2) {{
        for (var j = 0; j < h.length - 1; j++) {{
          if (q.indexOf(h.substring(j, j + 2)) !== -1) score += 0.3;
        }}
      }}
    }}
    return score;
  }}

  function answer(question) {{
    if (!question || !question.trim()) {{
      return {{ text: FALLBACK_ANSWER, source: null }};
    }}
    if (matchesGuardrailTest(question)) {{
      return {{ text: FALLBACK_ANSWER, source: null }};
    }}
    var best = null;
    var bestScore = 0;
    for (var i = 0; i < KB.length; i++) {{
      var s = scoreEntry(KB[i], question);
      if (s > bestScore) {{
        bestScore = s;
        best = KB[i];
      }}
    }}
    if (best && bestScore >= 1) {{
      return {{ text: best.answer, source: best.source }};
    }}
    return {{ text: FALLBACK_ANSWER, source: null }};
  }}

  function buildWidget() {{
    var launcher = document.createElement("button");
    launcher.id = "chatbot-launcher";
    launcher.type = "button";
    launcher.setAttribute("aria-label", {aria_label});
    launcher.textContent = "\\uD83D\\uDCAC";
    launcher.style.cssText =
      "position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;" +
      "background:#2C2C2A;color:#fff;border:none;font-size:22px;cursor:pointer;" +
      "box-shadow:0 2px 8px rgba(0,0,0,0.25);z-index:9999;";

    var modal = document.getElementById("chatbot-modal");
    var modalWasStatic = !!modal;
    if (!modal) {{
      modal = document.createElement("div");
      modal.id = "chatbot-modal";
      modal.setAttribute("data-kb-source", "07");
    }}
    modal.style.cssText =
      "position:fixed;right:20px;bottom:88px;width:320px;max-height:420px;display:none;" +
      "flex-direction:column;background:#fff;border:1px solid #D3D1C7;border-radius:12px;" +
      "box-shadow:0 4px 16px rgba(0,0,0,0.2);z-index:9999;overflow:hidden;font-family:sans-serif;";

    var header = document.createElement("div");
    header.textContent = {header_text};
    header.style.cssText = "padding:10px 12px;background:#1F2A44;color:#fff;font-size:14px;";

    var log = document.createElement("div");
    log.id = "chatbot-log";
    log.style.cssText = "flex:1;overflow-y:auto;padding:10px;font-size:13px;color:#2C2C2A;";

    var inputRow = document.createElement("div");
    inputRow.style.cssText = "display:flex;border-top:1px solid #D3D1C7;";

    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = {placeholder_text};
    input.style.cssText = "flex:1;border:none;padding:8px;font-size:13px;outline:none;";

    var sendBtn = document.createElement("button");
    sendBtn.type = "button";
    sendBtn.textContent = "\\uC804\\uC1A1";
    sendBtn.style.cssText = "border:none;background:#1F2A44;color:#fff;padding:0 12px;cursor:pointer;";

    function appendMessage(text, who) {{
      var msg = document.createElement("div");
      msg.style.cssText = "margin-bottom:8px;";
      msg.innerHTML =
        '<strong style="color:' + (who === "user" ? "#854F0B" : "#1F2A44") + '">' +
        (who === "user" ? "\\uB098" : "\\uC548\\uB0B4\\uC6D0") +
        "</strong>: " +
        text;
      log.appendChild(msg);
      log.scrollTop = log.scrollHeight;
    }}

    function handleSend() {{
      var q = input.value;
      if (!q.trim()) return;
      appendMessage(q, "user");
      input.value = "";
      var result = answer(q);
      var text = result.text;
      if (result.source) {{
        text += ' <span style="color:#8a8a86;font-size:11px;">(\\uCD9C\\uCC98: ' + result.source + ")</span>";
      }}
      appendMessage(text, "bot");
    }}

    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keydown", function (e) {{
      if (e.key === "Enter") handleSend();
    }});

    launcher.addEventListener("click", function () {{
      modal.style.display = modal.style.display === "none" ? "flex" : "none";
    }});

    inputRow.appendChild(input);
    inputRow.appendChild(sendBtn);
    modal.appendChild(header);
    modal.appendChild(log);
    modal.appendChild(inputRow);

    document.body.appendChild(launcher);
    if (!modalWasStatic) document.body.appendChild(modal);
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", buildWidget);
  }} else {{
    buildWidget();
  }}
}})();
"""
