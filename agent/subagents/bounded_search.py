"""bounded_search — 카드만으로는 부족한 사실의 출처를 신뢰할 수 있는 출처 유형으로만
좁혀서 보강 검색한다.

허용: 공공기관, 공식 사이트, 언론 기사, 학술 논문, 지도 서비스.
금지: 개인 블로그, 유튜브, 커뮤니티, 위키 등 누구나 편집 가능한 문서.

이중 방어로 금지 출처를 막는다:
1. Claude의 web_search 서버 도구 자체에 blocked_domains로 1차 차단.
2. 그래도 모델이 돌려준 출처 URL을 다시 한 번 도메인 문자열로 대조해 최종 판정
   (모델이 스스로 오분류해도 여기서 걸러지도록).

허용된 출처에서 명확한 사실을 찾지 못하면 지어내지 않고 found=False로만 둔다
(fact/source는 채우지 않는다). 호출 여부와 결과는 항상 로그로 남긴다.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger("agent.subagents.bounded_search")

_BLOCKED_DOMAINS = [
    "blog.naver.com", "tistory.com", "brunch.co.kr", "medium.com", "blogspot.com",
    "post.naver.com", "youtube.com", "youtu.be", "reddit.com", "dcinside.com",
    "clien.net", "fmkorea.com", "cafe.naver.com", "cafe.daum.net", "quora.com",
    "instiz.net", "wikipedia.org", "namu.wiki", "wikitree.co.kr",
]

_SOURCE_TYPE_PATTERNS = [
    (("go.kr", ".gov", ".mil"), "공공기관"),
    (("ac.kr", "riss.kr", "dbpia.co.kr", "doi.org", "jstor.org", "kci.go.kr", "scholar.google"), "학술 논문"),
    (("map.kakao.com", "map.naver.com", "google.com/maps", "maps.google"), "지도 서비스"),
    (
        (
            "yna.co.kr", "yonhapnews", "chosun.com", "joins.com", "hani.co.kr", "khan.co.kr",
            "ohmynews.com", "newsis.com", "ytn.co.kr", "kbs.co.kr", "imbc.com", "sbs.co.kr",
            "jejusori.net", "jejuilbo.net", "jemin.com", "ihalla.com",
        ),
        "언론 기사",
    ),
]

_SYSTEM_PROMPT = """너는 카드 밖 자료를 보강 검색하는 전용 도구다. 아래 출처 유형만 채택한다:
공공기관, 공식 사이트(정부·기관·단체의 공식 홈페이지), 언론 기사, 학술 논문, 지도 서비스.

절대 금지: 개인 블로그, 유튜브, 커뮤니티(카페·갤러리·포럼), 위키(위키백과·나무위키 등
누구나 편집 가능한 문서)는 절대 출처로 채택하지 마라 — 검색 결과에 이런 출처만 있다면
찾지 못한 것으로 처리하라. 지어내지 마라.

신뢰할 수 있는 출처에서 명확한 사실을 찾으면 정확히 아래 JSON 형식으로만 답하라:
{"found": true, "fact": "찾은 사실(간결하게, 지어내지 말고 실제로 찾은 내용만)",
 "source": "출처 URL 또는 정확한 발행처명", "source_type": "공공기관|공식 사이트|언론 기사|학술 논문|지도 서비스"}

허용된 출처에서 명확한 사실을 못 찾으면 지어내지 말고 정확히 아래로만 답하라:
{"found": false, "fact": "", "source": "", "source_type": ""}
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def _classify_source_type(url: str) -> str | None:
    for domains, label in _SOURCE_TYPE_PATTERNS:
        if any(d in url for d in domains):
            return label
    return None


def _is_blocked_domain(url: str) -> bool:
    return any(d in url for d in _BLOCKED_DOMAINS)


def bounded_search(query: str) -> dict:
    """query로 허용된 출처 유형만 검색해 {"found","fact","source","source_type"}를 반환한다.

    Claude의 web_search 서버 도구로 실제 인터넷을 검색하는, 이 함수 전용의 좁은
    스코프 Claude 호출을 한다(01-verify 본 요청과는 별개의 호출).
    """
    logger.info("bounded_search 호출: query=%r", query)

    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        logger.warning("bounded_search: ANTHROPIC_API_KEY가 없어 검색을 건너뜁니다 (found=False)")
        return {"found": False, "fact": "", "source": "", "source_type": ""}

    import anthropic

    from llm_client import DEFAULT_ANTHROPIC_MODEL

    client = _get_client()

    try:
        response = client.messages.create(
            model=DEFAULT_ANTHROPIC_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
            tools=[
                {
                    "type": "web_search_20260209",
                    "name": "web_search",
                    "max_uses": 3,
                    "blocked_domains": _BLOCKED_DOMAINS,
                }
            ],
        )
    except anthropic.APIError as exc:
        logger.warning("bounded_search: 검색 호출 실패(%s) - found=False로 처리", exc)
        return {"found": False, "fact": "", "source": "", "source_type": ""}

    raw_text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("bounded_search: 응답을 JSON으로 파싱하지 못함 - found=False로 처리. 원문: %r", raw_text[:200])
        return {"found": False, "fact": "", "source": "", "source_type": ""}

    if not data.get("found"):
        logger.info("bounded_search: 허용된 출처에서 사실을 찾지 못함 (found=False)")
        return {"found": False, "fact": "", "source": "", "source_type": ""}

    source = data.get("source", "")
    if _is_blocked_domain(source):
        logger.warning("bounded_search: 모델이 금지 출처(%s)를 반환해 서버에서 거부 - found=False로 처리", source)
        return {"found": False, "fact": "", "source": "", "source_type": ""}

    resolved_type = _classify_source_type(source) or data.get("source_type") or "공식 사이트"

    result = {
        "found": True,
        "fact": data.get("fact", ""),
        "source": source,
        "source_type": resolved_type,
    }
    logger.info("bounded_search 결과: found=True source_type=%s source=%s", resolved_type, source)
    return result
