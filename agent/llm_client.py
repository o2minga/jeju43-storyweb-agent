"""모델 호출이 모이는 단 하나의 지점.

바깥에 노출하는 건 call_model()과 generate_validated() 둘이다. agent/generate/의 각
스텝(step01_verify.py 등)은 anthropic이든 다른 SDK든 절대 직접 import하지 않고 이 함수들만
호출한다 — provider 종류·API 계약·재시도·로깅은 전부 이 파일 안에 갇혀 있고, 스텝 코드에는
provider 관련 코드가 한 줄도 남지 않는다.

provider는 LLM_PROVIDER 환경변수로 분기한다(기본값 "anthropic"). 새 provider를 추가하려면
_call_<provider>() 함수를 만들고 _PROVIDERS에 등록하면 된다 — 지금은 anthropic만 실제로
구현되어 있고 나머지는 자리만 잡아 뒀다(NotImplementedError).

call_model()은 JSON Schema만 알 뿐 pydantic을 전혀 모른다(구조 계약과 provider 분기만
담당). generate_validated()가 그 위에 pydantic 검증·재시도 한 겹을 얹는다 — "구조는
JSON Schema를 지켰지만 model_validator 같은 비즈니스 규칙은 어긴" 응답을 call_model()
혼자서는 걸러낼 수 없기 때문이다.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("agent.llm_client")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
MAX_RETRIES = 2
MAX_TOKENS = 8000
CLI_TIMEOUT_SEC = int(os.environ.get("CLAUDE_CLI_TIMEOUT_SEC", "600"))

_anthropic_client = None


def strip_frontmatter(text: str) -> str:
    """`.claude/agents/*.md`(또는 SKILL.md)의 선두 YAML frontmatter(`---`로 둘러싸인
    name/description/tools/model 등)를 걷어내고 본문만 반환한다. frontmatter가 없으면
    입력을 그대로 반환한다(안전한 no-op) — 시스템 프롬프트로 실제 모델에 넘길 때,
    Claude Code 전용 메타데이터(tools/model 등)가 프롬프트 텍스트에 섞여 들어가지
    않게 하기 위함이다."""
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return text
    parts = stripped.split("\n---", 1)
    if len(parts) != 2:
        return text
    return parts[1].lstrip("\n")


class LLMCallError(Exception):
    """call_model()이 복구하지 못한 상황(키 없음·거절·API 오류·반복된 파싱 실패 등)."""


@dataclass
class CallTelemetry:
    """가장 최근 generate_validated()/generate_validated_with_tools() 호출 1건의 계측치.

    run_agent.py가 각 스텝 실행 직후 get_last_telemetry()로 읽어가 logs/에 남긴다.
    LLM을 아예 안 부르는 스텝(03/04/05/06)이나, 파일이 이미 있어 이번 실행에는 호출이
    없었던 스텝에서는 reset_telemetry()로 초기화된 빈 값 그대로 남는다 — 이전 스텝의
    수치가 새어 들어가는 걸 막기 위해서다.
    """

    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_sec: float = 0.0
    prompt_preview: str = ""
    response_preview: str = ""
    tool_calls: list[str] = field(default_factory=list)
    error: str | None = None


_last_telemetry = CallTelemetry()


def _preview(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def get_last_telemetry() -> CallTelemetry:
    """가장 최근 LLM 호출의 계측치(시도 횟수·토큰 수·소요시간 등)를 반환한다."""
    return _last_telemetry


def reset_telemetry() -> None:
    """다음 스텝을 시작하기 전에 호출한다 — 이전 스텝의 계측치가 이번 스텝으로 새어
    들어가지 않게 초기화한다(예: 이번 스텝은 파일이 이미 있어 LLM을 아예 안 부르는 경우)."""
    global _last_telemetry
    _last_telemetry = CallTelemetry()


def call_model(system_prompt: str, user_input: str, output_schema: dict) -> dict:
    """system_prompt + user_input을 모델에 보내 output_schema를 따르는 JSON(dict)을 받는다.

    provider 분기, 실제 API 호출, JSON 파싱, 실패 시 재시도, 로깅을 전부 여기서 처리한다.
    output_schema는 JSON Schema(dict)다 — 보통 호출부가 `Model.model_json_schema()`로
    만들어 넘긴다. 반환값은 아직 pydantic으로 검증되지 않은 원본 dict이므로, 호출부가
    필요하면 자신의 스키마로 다시 검증한다(이 함수는 pydantic 모델을 모른다).
    """
    provider = os.environ.get("LLM_PROVIDER", "claude_cli")
    try:
        impl = _PROVIDERS[provider]
    except KeyError:
        raise LLMCallError(f"알 수 없는 LLM_PROVIDER: {provider!r} (지원: {sorted(_PROVIDERS)})") from None

    logger.info("call_model 시작: provider=%s system_len=%d user_len=%d", provider, len(system_prompt), len(user_input))
    data = impl(system_prompt, user_input, output_schema)
    logger.info("call_model 성공: provider=%s", provider)
    return data


ModelT = TypeVar("ModelT", bound=BaseModel)


def _format_validation_error(exc: ValidationError) -> str:
    lines = [f"검증 실패 ({exc.error_count()}건):"]
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(root)"
        lines.append(f"  - field: {loc}")
        lines.append(f"    reason: {err['msg']} (type={err['type']})")
    return "\n".join(lines)


def generate_validated(
    system_prompt: str,
    user_input: str,
    Model: type[ModelT],
    max_retries: int = 2,
) -> ModelT:
    """call_model() 결과를 Model로 검증하고, 실패하면 에러를 알려주며 재시도한다.

    1. Model.model_json_schema()로 스키마를 만들어 call_model()을 호출한다.
    2. 결과를 Model.model_validate()로 검증한다.
    3. ValidationError가 나면, 어느 필드가 왜 문제인지를 원래 user_input 뒤에 덧붙여
       call_model()을 다시 호출한다.
    4. max_retries까지 반복하고, 그래도 실패하면 마지막 ValidationError를 그대로 던진다.

    call_model() 자체는 pydantic을 모르는 채로 남는다 — 이 함수가 그 위에 한 겹 얹는다.

    호출할 때마다 get_last_telemetry()로 읽을 수 있는 계측치(시도 횟수·토큰 수·소요
    시간·프롬프트/응답 요약)를 새로 기록한다 — run_agent.py가 logs/에 남기는 데 쓴다.
    """
    global _last_telemetry
    _last_telemetry = CallTelemetry(prompt_preview=_preview(user_input))
    telemetry = _last_telemetry
    start = time.monotonic()

    schema = Model.model_json_schema()
    current_input = user_input
    last_error: ValidationError | None = None
    total_attempts = max_retries + 1

    for attempt in range(1, total_attempts + 1):
        telemetry.attempts = attempt
        data = call_model(system_prompt, current_input, schema)
        try:
            result = Model.model_validate(data)
        except ValidationError as exc:
            last_error = exc
            telemetry.error = str(exc)[:500]
            logger.warning(
                "generate_validated: %s 검증 실패 (시도 %d/%d)\n%s",
                Model.__name__,
                attempt,
                total_attempts,
                _format_validation_error(exc),
            )
            if attempt >= total_attempts:
                break
            current_input = (
                f"{user_input}\n\n"
                "---\n"
                "방금 응답은 JSON 구조 자체는 스키마를 따랐지만, 아래 이유로 검증에 실패했다:\n"
                f"{_format_validation_error(exc)}\n\n"
                "위 문제를 전부 고쳐서 완전한 JSON 하나로 처음부터 다시 답해줘."
            )
            continue

        telemetry.error = None
        telemetry.response_preview = _preview(json.dumps(data, ensure_ascii=False))
        telemetry.duration_sec = round(time.monotonic() - start, 3)
        logger.info("generate_validated: %s 검증 성공 (시도 %d/%d)", Model.__name__, attempt, total_attempts)
        return result

    telemetry.duration_sec = round(time.monotonic() - start, 3)
    logger.error("generate_validated: %s 최종 실패 (%d회 시도 모두 검증 실패)", Model.__name__, total_attempts)
    raise last_error


def generate_validated_with_tools(
    system_prompt: str,
    user_input: str,
    Model: type[ModelT],
    tools: list[dict],
    max_retries: int = 2,
    max_tool_iterations: int = 6,
) -> ModelT:
    """generate_validated()에 Claude 커스텀 tool_use를 더한 버전.

    tools는 [{"name", "description", "input_schema", "handler"}] 형태다. anthropic
    provider에서는 각 도구를 모델이 스스로 호출할지 판단한다(tool_choice 기본값
    "auto" — 미리 정해서 강제 호출하지 않는다). 도구 호출이 오면 로컬
    handler(**block.input)를 실행해 결과를 tool_result로 돌려주고, 최종 텍스트
    응답이 나오면 Model로 검증한다 — 검증 실패 시 generate_validated()와 동일하게
    에러를 알려주며 재시도한다.

    claude_cli provider(Phase C3)에서는 로컬 handler를 CLI 서브프로세스 경계 너머로
    넘길 수 없으므로(01의 bounded_search가 유일한 사용처), 커스텀 tool_use 루프
    대신 CLI 네이티브 WebSearch/WebFetch를 `--allowedTools`로 허용해 CLI가 스스로
    검색 필요 여부를 판단하게 한다 — bounded_search의 도메인 차단 이중검증은
    CLI 경로에서는 적용되지 않고, 허용/금지 출처 규칙은 system_prompt 본문에 이미
    있는 지시문에 의존한다(알려진 트레이드오프, 감사 보고서 Phase B/C3 참고).

    generate_validated()와 마찬가지로 호출마다 get_last_telemetry()에 계측치를 새로
    기록한다 — tool_calls에는 이번 호출에서 실제로 호출된 도구 이름이 순서대로 쌓인다
    (claude_cli 경로에서는 CLI 내부 도구 호출이라 이름을 개별적으로 알 수 없어 비워 둔다).
    """
    provider = os.environ.get("LLM_PROVIDER", "claude_cli")
    if provider not in ("anthropic", "claude_cli"):
        raise LLMCallError(f"generate_validated_with_tools는 anthropic/claude_cli provider만 지원합니다 (LLM_PROVIDER={provider!r})")

    global _last_telemetry
    _last_telemetry = CallTelemetry(prompt_preview=_preview(user_input))
    telemetry = _last_telemetry
    start = time.monotonic()

    schema = Model.model_json_schema()
    api_tools = [{"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]} for t in tools]
    handlers = {t["name"]: t["handler"] for t in tools}

    current_input = user_input
    last_error: ValidationError | None = None
    total_attempts = max_retries + 1

    for attempt in range(1, total_attempts + 1):
        telemetry.attempts = attempt
        if provider == "claude_cli":
            data = _call_claude_cli(system_prompt, current_input, schema, allowed_tools=["WebSearch", "WebFetch"])
        else:
            data = _call_anthropic_with_tool_loop(system_prompt, current_input, schema, api_tools, handlers, max_tool_iterations)
        try:
            result = Model.model_validate(data)
        except ValidationError as exc:
            last_error = exc
            telemetry.error = str(exc)[:500]
            logger.warning(
                "generate_validated_with_tools: %s 검증 실패 (시도 %d/%d)\n%s",
                Model.__name__,
                attempt,
                total_attempts,
                _format_validation_error(exc),
            )
            if attempt >= total_attempts:
                break
            current_input = (
                f"{user_input}\n\n"
                "---\n"
                "방금 응답은 JSON 구조 자체는 스키마를 따랐지만, 아래 이유로 검증에 실패했다:\n"
                f"{_format_validation_error(exc)}\n\n"
                "위 문제를 전부 고쳐서 완전한 JSON 하나로 처음부터 다시 답해줘."
            )
            continue

        telemetry.error = None
        telemetry.response_preview = _preview(json.dumps(data, ensure_ascii=False))
        telemetry.duration_sec = round(time.monotonic() - start, 3)
        logger.info("generate_validated_with_tools: %s 검증 성공 (시도 %d/%d)", Model.__name__, attempt, total_attempts)
        return result

    telemetry.duration_sec = round(time.monotonic() - start, 3)
    logger.error("generate_validated_with_tools: %s 최종 실패 (%d회 시도 모두 검증 실패)", Model.__name__, total_attempts)
    raise last_error


def _call_anthropic_with_tool_loop(
    system_prompt: str,
    user_input: str,
    output_schema: dict,
    api_tools: list[dict],
    handlers: dict,
    max_iterations: int,
) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        raise LLMCallError(
            "ANTHROPIC_API_KEY가 설정되어 있지 않습니다. "
            ".env.local에 ANTHROPIC_API_KEY=sk-ant-... 를 채우거나, "
            "환경 변수로 export한 뒤 다시 실행하세요."
        )

    import anthropic

    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    client = _anthropic_client

    messages = [{"role": "user", "content": user_input}]

    for _ in range(max_iterations):
        try:
            response = client.messages.create(
                model=DEFAULT_ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=messages,
                tools=api_tools,
                output_config={"format": {"type": "json_schema", "schema": output_schema}},
            )
        except anthropic.NotFoundError as exc:
            raise LLMCallError(f"모델을 찾을 수 없습니다({DEFAULT_ANTHROPIC_MODEL}): {exc}") from exc
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
            logger.warning("tool_use 루프: 재시도 가능한 오류(%s) — 그대로 재시도", exc)
            continue
        except anthropic.APIStatusError as exc:
            raise LLMCallError(f"Anthropic API 오류: {exc}") from exc

        usage = getattr(response, "usage", None)
        if usage is not None:
            _last_telemetry.input_tokens += getattr(usage, "input_tokens", 0) or 0
            _last_telemetry.output_tokens += getattr(usage, "output_tokens", 0) or 0

        if response.stop_reason == "refusal":
            raise LLMCallError(f"모델이 요청을 거절했습니다(stop_reason=refusal): {getattr(response, 'stop_details', None)}")

        if response.stop_reason == "tool_use":
            reasoning_text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()
            if reasoning_text:
                logger.info("tool_use 판단 이유(모델이 도구 호출 직전에 남긴 텍스트): %s", reasoning_text)
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                handler = handlers.get(block.name)
                if handler is None:
                    logger.warning("tool_use: 알 수 없는 도구 이름 %r — 에러로 응답", block.name)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": f"알 수 없는 도구: {block.name}"}),
                            "is_error": True,
                        }
                    )
                    continue
                logger.info("tool_use 호출됨: name=%s input=%r", block.name, block.input)
                _last_telemetry.tool_calls.append(block.name)
                try:
                    result_obj = handler(**block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result_obj, ensure_ascii=False),
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - 도구 실행 실패는 tool_result의 에러로 모델에 알려준다
                    logger.warning("tool_use 실행 실패: name=%s error=%s", block.name, exc)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": str(exc)}),
                            "is_error": True,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        logger.info("tool_use 없이 최종 응답 (등록된 도구를 이번 요청에서는 쓰지 않기로 판단함)")
        raw_text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMCallError(f"최종 응답이 유효한 JSON이 아닙니다: {exc}") from exc

    raise LLMCallError(f"tool_use 루프가 {max_iterations}회 반복 후에도 끝나지 않았습니다.")


def _call_anthropic(system_prompt: str, user_input: str, output_schema: dict) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        raise LLMCallError(
            "ANTHROPIC_API_KEY가 설정되어 있지 않습니다. "
            ".env.local에 ANTHROPIC_API_KEY=sk-ant-... 를 채우거나, "
            "환경 변수로 export한 뒤 다시 실행하세요."
        )

    import anthropic

    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    client = _anthropic_client

    messages = [{"role": "user", "content": user_input}]
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            response = client.messages.create(
                model=DEFAULT_ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=messages,
                output_config={"format": {"type": "json_schema", "schema": output_schema}},
            )
        except anthropic.NotFoundError as exc:
            raise LLMCallError(f"모델을 찾을 수 없습니다({DEFAULT_ANTHROPIC_MODEL}): {exc}") from exc
        except anthropic.RateLimitError as exc:
            logger.warning("anthropic RateLimitError (시도 %d/%d): %s", attempt, MAX_RETRIES + 1, exc)
            last_error = exc
            continue
        except anthropic.APIConnectionError as exc:
            logger.warning("anthropic APIConnectionError (시도 %d/%d): %s", attempt, MAX_RETRIES + 1, exc)
            last_error = exc
            continue
        except anthropic.APIStatusError as exc:
            raise LLMCallError(f"Anthropic API 오류: {exc}") from exc

        usage = getattr(response, "usage", None)
        if usage is not None:
            _last_telemetry.input_tokens += getattr(usage, "input_tokens", 0) or 0
            _last_telemetry.output_tokens += getattr(usage, "output_tokens", 0) or 0

        if response.stop_reason == "refusal":
            raise LLMCallError(f"모델이 요청을 거절했습니다(stop_reason=refusal): {getattr(response, 'stop_details', None)}")

        raw_text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("JSON 파싱 실패 (시도 %d/%d): %s", attempt, MAX_RETRIES + 1, exc)
            last_error = exc
            messages.append({"role": "assistant", "content": raw_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"방금 출력이 올바른 JSON이 아니었습니다: {exc}\n"
                        "스키마에 맞는 완전한 JSON 하나로 처음부터 다시 답해줘."
                    ),
                }
            )

    raise LLMCallError(f"{MAX_RETRIES + 1}번 시도 후에도 유효한 JSON을 받지 못했습니다: {last_error}")


def _call_claude_cli(
    system_prompt: str,
    user_input: str,
    output_schema: dict,
    allowed_tools: list[str] | None = None,
) -> dict:
    """claude CLI를 서브프로세스로 호출해 구조화 출력을 받는다 — host subagent 메커니즘
    (Phase C3, 감사 보고서 A3 참고). ANTHROPIC_API_KEY 없이 Claude Code 구독 로그인으로
    동작한다(non-bare 모드 — bare는 구독 로그인을 인정하지 않는다).

    `--agent <name>`으로 직접 커스텀 서브에이전트를 호출하면 `--json-schema`가 무시되는
    현상이 확인되어(트리비얼 스키마·실제 스키마 둘 다 재현), 대신 시스템 프롬프트
    본문을 `--append-system-prompt-file`로 주입하고 `--json-schema`로 구조화 출력을
    강제하는 방식을 쓴다. 이 함수에 들어오는 system_prompt는 이미 frontmatter가
    제거된 상태라고 가정한다(strip_frontmatter() 참고).

    allowed_tools가 없으면(기본값) `--allowedTools ""`로 도구 사용을 완전히 막아 기존
    anthropic 경로와 동일한 순수 텍스트-in/JSON-out 호출을 재현한다. allowed_tools가
    있으면(01의 bounded_search 대체 — 아래 generate_validated_with_tools 참고) 그
    이름들만 허용해 CLI가 스스로 검색 필요 여부를 판단하게 한다.
    """
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise LLMCallError("claude CLI를 찾을 수 없습니다 (PATH에 설치되어 있는지 확인하세요).")

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    schema_json = json.dumps(output_schema, ensure_ascii=False)
    allowed_tools_str = " ".join(allowed_tools) if allowed_tools else ""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8", prefix="claude-cli-sysprompt-"
    ) as f:
        f.write(system_prompt)
        sysprompt_path = f.name

    try:
        cmd = [
            claude_bin, "-p",
            "--append-system-prompt-file", sysprompt_path,
            "--model", model,
            "--allowedTools", allowed_tools_str,
            "--output-format", "json",
            "--json-schema", schema_json,
        ]
        try:
            proc = subprocess.run(
                cmd, input=user_input, capture_output=True, text=True, encoding="utf-8",
                timeout=CLI_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMCallError(f"claude CLI 호출이 {CLI_TIMEOUT_SEC}초 안에 끝나지 않았습니다.") from exc
    finally:
        try:
            os.unlink(sysprompt_path)
        except OSError:
            pass

    if proc.returncode != 0:
        raise LLMCallError(f"claude CLI가 비정상 종료했습니다(exit={proc.returncode}): {proc.stderr[:500]}")

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise LLMCallError(f"claude CLI 출력이 JSON이 아닙니다: {exc}\n{proc.stdout[:500]}") from exc

    if payload.get("is_error"):
        raise LLMCallError(f"claude CLI가 오류를 반환했습니다: {payload.get('result')}")

    structured = payload.get("structured_output")
    if structured is None:
        raise LLMCallError("claude CLI 응답에 structured_output이 없습니다 (--json-schema가 적용되지 않음).")

    usage = payload.get("usage") or {}
    _last_telemetry.input_tokens += (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
    )
    _last_telemetry.output_tokens += usage.get("output_tokens") or 0
    _last_telemetry.cost_usd += payload.get("total_cost_usd") or 0.0

    return structured


def _call_openai(system_prompt: str, user_input: str, output_schema: dict) -> dict:
    raise NotImplementedError("LLM_PROVIDER=openai는 아직 구현되지 않았습니다.")


def _call_gemini(system_prompt: str, user_input: str, output_schema: dict) -> dict:
    raise NotImplementedError("LLM_PROVIDER=gemini는 아직 구현되지 않았습니다.")


_PROVIDERS = {
    "anthropic": _call_anthropic,
    "claude_cli": _call_claude_cli,
    "openai": _call_openai,
    "gemini": _call_gemini,
}
