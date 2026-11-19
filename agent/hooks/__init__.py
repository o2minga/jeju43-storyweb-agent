"""파이프라인 콜백(hook) 레지스트리 — 순수 dict/list 기반, 외부 라이브러리 불필요.

Flask의 before_request/after_request, Django의 signal, Airflow의 callback과 같은
개념이다: run_agent.py 본체는 "이 시점에 등록된 콜백이 있으면 실행해라"만 알면 되고,
실제로 무엇을 실행할지는 register()로 미리 등록해둔 콜백들이 결정한다.

이벤트 이름은 미리 정해진 목록이 아니다 — register()/fire()에 아무 문자열이나 쓰면
그 자리에서 새 이벤트가 생긴다. run_agent.py는 지금 "before_step"/"after_step"/
"on_complete" 세 시점에서만 fire()를 호출한다:
  - "before_step": step_id, location_id, index, total
  - "after_step": step_id, location_id, status("pass"|"fail"), need_generate,
    result(검증된 모델/구조 요약, 실패 시 None), data(원본 산출물 — JSON 스텝은 dict,
    HTML 스텝은 원문 문자열. 얻지 못했으면 None), error(실패 시 메시지, 성공 시 None)
  - "on_complete": location_id, results(전 스텝 결과 dict)

주의: "after_step"의 status는 "이 스텝이 스키마에 맞는 결과물을 만들었는가"(구조적
성공)만 본다. 08(검수)처럼 구조적으로는 통과("pass")해도 콘텐츠 판정은 HOLD·
needs_human일 수 있다 — 그 판정이 필요하면 status가 아니라 result 안의 실제 필드
(예: result.overall_status, result.checks[].status)를 직접 봐야 한다.

콜백 하나가 예외를 던져도 파이프라인 자체는 멈추지 않는다 — 경고만 로그로 남기고
나머지 콜백·본 실행을 계속한다(관찰용 부가 로직이 핵심 파이프라인을 막으면 안 됨).
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("agent.hooks")

Callback = Callable[..., None]

_registry: dict[str, list[Callback]] = {}


def register(event: str, callback: Callback | None = None):
    """event 시점에 callback을 등록한다.

    두 가지 방식 모두 지원한다:
        hooks.register("before_step", my_callback)
    또는 데코레이터로:
        @hooks.register("after_step")
        def my_callback(**ctx): ...
    """
    if callback is None:
        def decorator(fn: Callback) -> Callback:
            _registry.setdefault(event, []).append(fn)
            return fn
        return decorator

    _registry.setdefault(event, []).append(callback)
    return callback


def unregister(event: str, callback: Callback) -> None:
    """등록을 취소한다 — 주로 테스트에서 정리용으로 쓴다."""
    if event in _registry and callback in _registry[event]:
        _registry[event].remove(callback)


def clear(event: str | None = None) -> None:
    """event 하나만, 또는(생략 시) 등록된 모든 콜백을 지운다 — 테스트 격리용."""
    if event is None:
        _registry.clear()
    else:
        _registry.pop(event, None)


def registered(event: str) -> list[Callback]:
    """event에 등록된 콜백 목록(등록 순서)을 반환한다 — 읽기 전용 조회용."""
    return list(_registry.get(event, []))


def fire(event: str, **context: Any) -> None:
    """event에 등록된 콜백을 등록 순서대로 전부 실행한다.

    context는 콜백에 키워드 인자로 그대로 전달된다. 콜백 하나가 실패해도 나머지
    콜백과 파이프라인 실행은 계속된다 — 예외는 로그로만 남긴다.
    """
    for callback in _registry.get(event, []):
        try:
            callback(**context)
        except Exception:  # noqa: BLE001 - 콜백 실패가 파이프라인을 막으면 안 됨
            logger.exception(
                "hook 콜백 실행 실패: event=%r callback=%r", event, getattr(callback, "__name__", callback)
            )
