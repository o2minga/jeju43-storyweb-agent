"""05-assemble 실제 생성 — Group C(조립형): Claude를 호출하지 않고, 01·02·03·04의 이미
검증된 JSON을 skills/05-assemble/spec.md 5장의 마크업 규칙에 맞춰 정적 .html로 조립한다.

핵심 로직: 02의 sources_by_sentence[].text_snippet.ko는 항상 해당 문단(intro/development/
closing)의 부분 문자열이어야 한다는 규칙을 이용해, 문단 텍스트 안에서 그 부분만
<span class="fact" data-fact-id data-source>로 감싸고 나머지는 평문으로 둔다. fact_id는
01의 verified_facts 중 같은 source.ref를 가진 항목과 매칭한다(여러 개면 본문 겹침이 가장
큰 것을 고른다) — 매칭되는 항목이 없으면 문장 자체가 유일하게 가진 비어있지 않은 값인
sentence_id를 fact_id로 대신 써서, "data-fact-id는 항상 비어있지 않아야 한다"는 05의
구조적 규칙을 지어낸 사실 없이도 지킨다.

이중언어(ko/en) 렌더링: `output/design/archive.css`(관덕정·곤을동·너븐숭이에 실제 적용된
아이보리 리디자인)가 이미 `.lang-ko`/`.lang-en`(block류), `.lang-ko-inline`/
`.lang-en-inline`(span류) 토글 CSS를 갖추고 있어, 이 모듈은 두 언어 블록을 항상 같이
만들어 둔다. en 데이터가 비어 있으면(예: 아직 번역 안 된 장소, 이미지 caption.en) 그
언어 블록은 아예 만들지 않는다 — 빈 번역을 지어내지 않고, 없으면 없는 대로 둔다.

문단 안 영문 출처 인용("[Source: ...]")은 01의 SourceEntry.ref_en(선택 필드)이 채워진
경우에만, 그 문단이 실제로 근거한 출처를 문단 끝에 한 번에 모아 붙인다 — ming의 원래
페이지는 문장 단위로 인용을 붙였지만, 그건 번역 과정에서 생긴 손 작업이라 정확히
재현할 데이터가 없다. "이야기 확인 퀴즈"는 02.quiz(선택 필드, 기본값 빈 배열)가 채워져
있으면 그대로 렌더링한다 — 비어 있으면(아직 생성 안 된 장소) 섹션 자체를 만들지 않는다.
"""
from __future__ import annotations

import html as _html
import logging
import os
from datetime import datetime, timezone

from schema.step01_verify import Step01VerifyOutput
from schema.step02_story import SourceBySentence, Step02StoryOutput
from schema.step03_visual import Step03VisualOutput, VisualAsset
from schema.step04_audio import Step04AudioOutput

logger = logging.getLogger("agent.generate.step05_assemble")

# 04(음향감독)가 실제로 쓰는 source 문구의 영문 번역 — 이 프로젝트가 직접 만든 고정
# 문자열이라(사용자 발화가 아님) 번역해도 지어내기가 아니다. 목록에 없는 문구(예: 앞으로
# audio_backend.py가 새 문구를 추가하는 경우)는 그냥 한국어 원문을 그대로 보여준다.
_AUDIO_SOURCE_EN = {
    "AI TTS (Microsoft Heami Desktop, ko-KR, Windows SAPI 오프라인 합성)": (
        "AI TTS (Microsoft Heami Desktop, ko-KR, offline synthesis via Windows SAPI — Korean only)"
    ),
    "AI TTS (관리자가 직접 지정한 오디오 파일)": "AI TTS (audio file manually provided by an administrator)",
    "AI TTS (placeholder)": "AI TTS (placeholder)",
    "자체 생성 앰비언트 패드 (numpy 합성, 로열티 프리)": (
        "self-generated ambient pad (synthesized with numpy, royalty-free)"
    ),
    "자체 생성 BGM (관리자가 직접 지정한 오디오 파일)": "self-generated BGM (audio file manually provided by an administrator)",
    "자체 AI 생성 BGM (placeholder)": "self-generated BGM (placeholder)",
}


def _escape(text: str) -> str:
    return _html.escape(text, quote=False)


def _relpath(location_id: str, full_path: str) -> str:
    """05-assemble.html(=output/{location_id}/05-assemble.html) 기준 상대 경로로 바꾼다."""
    output_prefix = f"output/{location_id}/"
    if full_path.startswith(output_prefix):
        return full_path[len(output_prefix):]
    # 03-visual의 관리자 반자동 워크플로우 자산은 output/ 밖 프로젝트 루트의
    # assets/{location_id}/에 놓인다 — output/{location_id}/에서 보면 두 단계 위로
    # 올라가야 한다(output/{location_id}/ → output/ → 프로젝트 루트).
    assets_prefix = f"assets/{location_id}/"
    if full_path.startswith(assets_prefix):
        return f"../../{full_path}"
    return full_path


def _find_fact_id(entry: SourceBySentence, verified_facts) -> str | None:
    # 01과 02가 같은 출처를 조금 다른 길이로 표기할 수 있어(예: "...·안내판 조사보고서" 접미사
    # 유무) 완전 일치 대신 양방향 부분 문자열 포함으로 매칭한다.
    candidates = [
        f
        for f in verified_facts
        if f.source.ref == entry.source or f.source.ref in entry.source or entry.source in f.source.ref
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0].fact_id

    def overlap(fact) -> int:
        return len(set(entry.text_snippet.ko) & set(fact.text))

    return max(candidates, key=overlap).fact_id


def _wrap_fact_spans(paragraph: str, entries: list[SourceBySentence], verified_facts) -> tuple[str, list[str]]:
    """반환값: (조립된 html, 이 문단 안에서 끝내 span으로 감싸지 못한 sentence_id 목록).

    entries는 이미 generate()에서 "이 문단의 부분 문자열"이라고 확인된 것들이지만,
    두 문장의 스니펫이 겹치는 구간을 가리키는 드문 경우 뒤쪽 문장은 span으로 감싸지
    못하고 밀려난다 — 이것도 "매칭 실패"로 취급해 반환한다(조용히 버리지 않는다).
    """
    matches = []
    unmatched: list[str] = []
    for entry in entries:
        snippet = entry.text_snippet.ko
        if not snippet:
            unmatched.append(entry.sentence_id)
            continue
        idx = paragraph.find(snippet)
        if idx != -1:
            matches.append((idx, idx + len(snippet), entry))
        else:
            unmatched.append(entry.sentence_id)
    matches.sort(key=lambda m: m[0])

    resolved = []
    last_end = 0
    for start, end, entry in matches:
        if start < last_end:
            unmatched.append(entry.sentence_id)
            continue
        resolved.append((start, end, entry))
        last_end = end

    pieces = []
    cursor = 0
    for start, end, entry in resolved:
        pieces.append(_escape(paragraph[cursor:start]))
        fact_id = _find_fact_id(entry, verified_facts) or entry.sentence_id
        pieces.append(
            f'<span class="fact" data-fact-id="{_escape(fact_id)}" data-source="{_escape(entry.source)}" '
            f'title="{_escape(entry.source)}">'
            f"{_escape(paragraph[start:end])}</span>"
        )
        cursor = end
    pieces.append(_escape(paragraph[cursor:]))
    return "".join(pieces), unmatched


def _asset_caption_html(asset: VisualAsset) -> str:
    ko = _escape(asset.caption.ko)
    parts = [f'<span class="lang-ko-inline">{ko}</span>']
    if asset.caption.en:
        parts.append(f'<span class="lang-en-inline" lang="en">{_escape(asset.caption.en)}</span>')
    return "".join(parts)


def _build_hero_html(location_id: str, location_name, hero_asset: VisualAsset | None) -> str:
    name_html = f'<span class="lang-ko-inline">{_escape(location_name.ko)}</span>'
    if location_name.en:
        name_html += f'<span class="lang-en-inline" lang="en">{_escape(location_name.en)}</span>'

    figure_html = ""
    if hero_asset is not None:
        src = _escape(_relpath(location_id, hero_asset.path))
        alt = _escape(hero_asset.caption.ko.replace("[연출]", "").strip())
        # is_ai_generated일 때만 "ai-generated" 클래스를 붙인다 — 이 클래스가 있으면
        # archive.css가 "[연출]/Staged" 배지를 자동으로 얹으므로, 실제 문헌(archival)
        # 사진에 붙이면 "사실 vs 연출 구분"이 깨진다(진짜 기록 사진을 AI 연출처럼 보이게 함).
        origin = "ai" if hero_asset.is_ai_generated else "archive"
        figure_class = "ai-generated hero-figure" if hero_asset.is_ai_generated else "hero-figure"
        figure_html = (
            f'<figure class="{figure_class}" data-origin="{origin}">\n'
            f'    <div class="hero-media">\n'
            f'      <img src="{src}" alt="{alt}">\n'
            f"    </div>\n"
            f"    <figcaption>{_asset_caption_html(hero_asset)}</figcaption>\n"
            f"  </figure>\n  "
        )

    return (
        '<header class="story-hero">\n  '
        f"{figure_html}"
        '<div class="story-hero-overlay">\n'
        '      <span class="overline">JEJU 4·3 STORY</span>\n'
        f"      <h1>{name_html}</h1>\n"
        "    </div>\n"
        "  </header>"
    )


def _build_visuals_html(location_id: str, rest_assets: list[VisualAsset]) -> str:
    if not rest_assets:
        return ""
    figures = []
    for asset in rest_assets:
        src = _escape(_relpath(location_id, asset.path))
        alt = _escape(asset.caption.ko.replace("[연출]", "").strip())
        origin = "ai" if asset.is_ai_generated else "archive"
        figure_class = "ai-generated" if asset.is_ai_generated else "archival"
        caption_html = _asset_caption_html(asset)
        if not asset.is_ai_generated:
            caption_html += f' <span class="lang-ko-inline">(출처: {_escape(asset.source)})</span>'
        figures.append(
            f'<figure class="{figure_class}" data-origin="{origin}">\n'
            f'  <img src="{src}" alt="{alt}">\n'
            f"  <figcaption>{caption_html}</figcaption>\n"
            f"</figure>"
        )
    return '<section class="visuals">\n' + "\n".join(figures) + "\n</section>"


def _build_bilingual_section(css_class: str, segment: str, ko_html: str, en_text: str, source_refs_en: list[str]) -> str:
    """source_refs_en: 이 문단에서 실제로 쓰인 출처의 영문 표기(ref_en) 목록, 없는 건 이미
    걸러진 상태로 들어온다. ming의 원래 페이지는 문장 단위로 인용을 붙였지만, 그건
    번역 과정에서 생긴 손 작업이라 데이터로 정확히 재현할 수 없다 — 대신 문단 전체에
    한 번, 그 문단이 근거한 출처를 모아 인용한다(더 거칠지만 지어내지 않는 선에서
    최대한 근접한 재현)."""
    if not en_text:
        return f'<section class="{css_class}" data-segment="{segment}">\n    <p class="lang-ko">{ko_html}</p>\n  </section>'

    citation = f' <span class="src-en">[Source: {_escape("; ".join(source_refs_en))}]</span>' if source_refs_en else ""
    return (
        f'<section class="{css_class}" data-segment="{segment}">\n'
        f'    <p class="lang-ko">{ko_html}</p>\n'
        f'    <p class="lang-en" lang="en">{_escape(en_text)}{citation}</p>\n'
        "  </section>"
    )


def _build_timeline_html(step02: Step02StoryOutput) -> str:
    if not step02.timeline_events:
        return ""
    rows = []
    for e in step02.timeline_events:
        ko_line = f"<strong>{_escape(e.date)}</strong> — {_escape(e.title.ko)}: {_escape(e.description.ko)}"
        parts = [f'<span class="lang-ko-inline">{ko_line}</span>']
        if e.title.en or e.description.en:
            en_line = f"<strong>{_escape(e.date)}</strong> — {_escape(e.title.en)}: {_escape(e.description.en)}"
            parts.append(f'<span class="lang-en-inline" lang="en">{en_line}</span>')
        rows.append(f'<div class="timeline-event" data-event-id="{_escape(e.event_id)}">{"".join(parts)}</div>')
    return '<div class="timeline">\n' + "\n".join(rows) + "\n</div>"


_QUIZ_SCRIPT = """
  <script>
    (function () {
      // 이야기 확인 퀴즈 — 정답/오답 표시 후 설명 노출, 임의로 다시 풀 수 없게 잠금
      document.querySelectorAll(".quiz-q").forEach(function (q) {
        var answer = q.dataset.answer;
        var buttons = q.querySelectorAll("button.choice");
        var explain = q.querySelector(".explain");
        buttons.forEach(function (choiceBtn) {
          choiceBtn.addEventListener("click", function () {
            if (q.dataset.answered) return;
            q.dataset.answered = "1";
            buttons.forEach(function (b) {
              if (b.dataset.choice === answer) b.classList.add("correct");
              else if (b === choiceBtn) b.classList.add("incorrect");
              b.disabled = true;
            });
            if (explain) explain.classList.add("show");
          });
        });
      });
    })();
  </script>"""


def _build_conflicts_html(conflicts) -> str:
    """01/02가 이미 갖고 있는 conflicts_carried_forward를 표로 보여준다 — "충돌 시 병기"
    (공통 규칙 5번)를 지키기 위해 이미 검증된 데이터인데, 지금까지는 만들어만 두고
    05가 렌더링하지 않고 있었다. ming이 손으로 만든 페이지의 표(출처별 열로 교차 정리)
    만큼 다듬어져 있지는 않지만(그건 카드마다 다른 손 편집이라 일반화하기 어렵다),
    같은 데이터를 topic별로 보여준다는 목적은 동일하게 달성한다. how_handled가
    LangText가 아니라 문자열 하나뿐이라 이 박스 자체는 한국어로만 표시한다."""
    if not conflicts:
        return ""
    boxes = []
    for c in conflicts:
        rows = "\n".join(
            f"        <tr><td>{_escape(v.source)}</td><td>{_escape(v.value)}</td></tr>" for v in c.values
        )
        boxes.append(
            f'  <div class="conflict-box" data-conflict-topic="{_escape(c.topic)}">\n'
            f"    <h4>⚖️ 기록마다 다릅니다 — {_escape(c.topic)}</h4>\n"
            "    <table>\n"
            "      <tr><th>출처</th><th>기록</th></tr>\n"
            f"{rows}\n"
            "    </table>\n"
            f"    <p>{_escape(c.how_handled)}</p>\n"
            "  </div>"
        )
    return "\n".join(boxes)


def _build_quiz_html(quiz) -> str:
    if not quiz:
        return ""
    blocks = []
    for i, q in enumerate(quiz, start=1):
        choice_buttons = []
        for c in q.choices:
            label = f'<span class="lang-ko-inline">{_escape(c.text.ko)}</span>'
            if c.text.en:
                label += f'<span class="lang-en-inline" lang="en">{_escape(c.text.en)}</span>'
            choice_buttons.append(f'        <button class="choice" data-choice="{_escape(c.choice_id)}">{label}</button>')

        question_en = (
            f'<span class="lang-en-inline" lang="en">Q{i}. {_escape(q.question.en)}</span>' if q.question.en else ""
        )
        explain_en = (
            f'<span class="lang-en-inline" lang="en">{_escape(q.explanation.en)}</span>' if q.explanation.en else ""
        )
        blocks.append(
            f'    <div class="quiz-q" data-answer="{_escape(q.correct_choice_id)}">\n'
            f'      <p class="q-text"><span class="lang-ko-inline">Q{i}. {_escape(q.question.ko)}</span>{question_en}</p>\n'
            '      <div class="choices">\n' + "\n".join(choice_buttons) + "\n      </div>\n"
            f'      <p class="explain"><span class="lang-ko-inline">{_escape(q.explanation.ko)}</span>{explain_en}</p>\n'
            "    </div>"
        )

    return (
        '<section class="quiz-section">\n'
        '    <h3><span class="lang-ko-inline">🌼 이야기 확인 퀴즈</span>'
        '<span class="lang-en-inline" lang="en">🌼 Story Check Quiz</span></h3>\n'
        + "\n".join(blocks)
        + "\n  </section>"
    )


def _build_audio_html(location_id: str, step04: Step04AudioOutput | None) -> str:
    if not step04 or step04.narration is None:
        return ""
    narration_src = _escape(_relpath(location_id, step04.narration.path))
    bgm_src = _escape(_relpath(location_id, step04.bgm.path))
    volume = step04.bgm.volume_relative_to_narration
    volume_pct = int(round(volume * 100))

    narration_source_en = _AUDIO_SOURCE_EN.get(step04.narration.source, step04.narration.source)
    bgm_source_en = _AUDIO_SOURCE_EN.get(step04.bgm.source, step04.bgm.source)

    # 마지막 구간의 end는 Infinity로 열어둔다 — 실제 재생 길이가 문서화된 값보다 약간
    # 길어도(부동소수점 오차 등) 낭독이 끝날 때까지 하이라이트가 계속 켜져 있게 하기 위함.
    timeline = step04.sync_timeline
    sync_entries = ",\n        ".join(
        f'{{ id: "{_escape(s.segment_id)}", start: {s.start_sec}, '
        f'end: {"Infinity" if i == len(timeline) - 1 else s.end_sec} }}'
        for i, s in enumerate(timeline)
    ) or '{ id: "", start: 0, end: 0 }'

    return f'''<section class="audio-player">
  <audio id="narrationAudio" controls src="{narration_src}"></audio>
  <audio id="bgmAudio" class="bgm" src="{bgm_src}" loop style="display:none"></audio>
  <p class="audio-note">
    <span class="lang-ko-inline">낭독: {_escape(step04.narration.source)} · 배경음악: {_escape(step04.bgm.source)}(낭독 대비 음량 {volume_pct}%)</span>
    <span class="lang-en-inline" lang="en">Narration: {_escape(narration_source_en)} · BGM: {_escape(bgm_source_en)} ({volume_pct}% volume relative to narration)</span>
  </p>
  <script>
    (function () {{
      var narration = document.getElementById("narrationAudio");
      var bgm = document.getElementById("bgmAudio");
      if (!narration || !bgm) return;
      bgm.volume = {volume};
      narration.addEventListener("play", function () {{ bgm.play().catch(function () {{}}); }});
      narration.addEventListener("pause", function () {{ bgm.pause(); }});
      narration.addEventListener("ended", function () {{ bgm.pause(); bgm.currentTime = 0; }});

      // 낭독 자막 하이라이트 — 04-audio.json의 sync_timeline을 그대로 쓴다.
      var SYNC_TIMELINE = [
        {sync_entries}
      ];
      var segmentEls = {{}};
      SYNC_TIMELINE.forEach(function (seg) {{
        segmentEls[seg.id] = document.querySelector('[data-segment="' + seg.id + '"]');
      }});
      function updateHighlight() {{
        var t = narration.currentTime;
        SYNC_TIMELINE.forEach(function (seg) {{
          var el = segmentEls[seg.id];
          if (el) el.classList.toggle("narration-active", t >= seg.start && t < seg.end);
        }});
      }}
      function clearHighlight() {{
        SYNC_TIMELINE.forEach(function (seg) {{
          if (segmentEls[seg.id]) segmentEls[seg.id].classList.remove("narration-active");
        }});
      }}
      narration.addEventListener("timeupdate", updateHighlight);
      narration.addEventListener("seeked", updateHighlight);
      narration.addEventListener("ended", clearHighlight);
    }})();
  </script>
</section>'''


def _build_sources_footer(step01: Step01VerifyOutput, used_refs: set[str]) -> str:
    used_for_map = {s.ref: s.used_for for s in step01.sources}
    used_for_en_map = {s.ref: s.used_for_en for s in step01.sources}
    items = []
    for ref in sorted(used_refs):
        label = used_for_map.get(ref, ref)
        label_en = used_for_en_map.get(ref, "")
        content = f'<span class="lang-ko-inline">{_escape(label)}</span>'
        if label_en:
            content += f'<span class="lang-en-inline" lang="en">{_escape(label_en)}</span>'
        else:
            # 영문 번역이 없으면 한국어라도 보이게 한다 — 출처 목록이 영어 모드에서
            # 통째로 안 보이는 것보다는, 번역 안 된 한국어 표기가 남아있는 게 낫다
            # (없는 번역을 지어내는 것과는 다르다 — 그냥 원문을 그대로 보여줄 뿐).
            content += f'<span class="lang-en-inline" lang="en">{_escape(label)}</span>'
        items.append(f'<li data-source-ref="{_escape(ref)}">{content}</li>')
    return '<footer class="sources">\n<ul>\n' + "\n".join(items) + "\n</ul>\n</footer>"


def generate(
    location_id: str,
    step01: Step01VerifyOutput,
    step02: Step02StoryOutput,
    step03: Step03VisualOutput | None,
    step04: Step04AudioOutput | None,
    chatbot_modal_relpath: str = "chatbot-modal.js",
) -> str:
    facts = step01.verified_facts
    paragraphs = {
        "intro": step02.story.intro.ko,
        "development": step02.story.development.ko,
        "closing": step02.story.closing.ko,
    }
    entries_by_section: dict[str, list[SourceBySentence]] = {k: [] for k in paragraphs}
    unmatched_sentence_ids: list[str] = []
    for entry in step02.sources_by_sentence:
        snippet = entry.text_snippet.ko
        matched_section = None
        if snippet:
            for section, paragraph in paragraphs.items():
                if snippet in paragraph:
                    matched_section = section
                    break
        if matched_section:
            entries_by_section[matched_section].append(entry)
        else:
            # 어느 문단에도 부분 문자열로 존재하지 않는 문장 — 조용히 버리지 않고 기록해서
            # 아래에서 html에 진단 마커로 남긴다(agent/schema/step05_assemble.py가 검증
            # 단계에서 이를 읽어 fail로 잡는다).
            unmatched_sentence_ids.append(entry.sentence_id)

    intro_html, unmatched_intro = _wrap_fact_spans(paragraphs["intro"], entries_by_section["intro"], facts)
    dev_html, unmatched_dev = _wrap_fact_spans(paragraphs["development"], entries_by_section["development"], facts)
    closing_html, unmatched_closing = _wrap_fact_spans(paragraphs["closing"], entries_by_section["closing"], facts)
    unmatched_sentence_ids += unmatched_intro + unmatched_dev + unmatched_closing

    used_refs = {e.source for e in step02.sources_by_sentence}
    internal_meta = '<meta name="internal-only" content="true">' if step01.publication_flag.internal_only else ""
    location_name_ko = step02.location_name.ko or location_id
    location_name_en = step02.location_name.en
    ref_en_map = {s.ref: s.ref_en for s in step01.sources}

    def _section_refs_en(section: str) -> list[str]:
        seen: list[str] = []
        for entry in entries_by_section[section]:
            ref_en = ref_en_map.get(entry.source, "")
            if ref_en and ref_en not in seen:
                seen.append(ref_en)
        return seen

    hero_asset, rest_assets = (None, [])
    if step03 and step03.assets:
        hero_asset, rest_assets = step03.assets[0], step03.assets[1:]

    hero_html = _build_hero_html(location_id, step02.location_name, hero_asset)
    visuals_html = _build_visuals_html(location_id, rest_assets)
    timeline_html = _build_timeline_html(step02)
    intro_section = _build_bilingual_section(
        "story-intro", "intro", intro_html, step02.story.intro.en, _section_refs_en("intro")
    )
    dev_section = _build_bilingual_section(
        "story-development", "development", dev_html, step02.story.development.en, _section_refs_en("development")
    )
    conflicts_html = _build_conflicts_html(step02.conflicts_carried_forward)
    closing_section = _build_bilingual_section(
        "story-closing", "closing", closing_html, step02.story.closing.en, _section_refs_en("closing")
    )
    audio_html = _build_audio_html(location_id, step04)
    quiz_html = _build_quiz_html(step02.quiz)
    quiz_script = _QUIZ_SCRIPT if step02.quiz else ""
    sources_html = _build_sources_footer(step01, used_refs)

    unmatched_marker = ""
    if unmatched_sentence_ids:
        ids_attr = ",".join(_escape(s) for s in unmatched_sentence_ids)
        unmatched_marker = f'\n  <div id="unmatched-fact-sentences" hidden data-sentence-ids="{ids_attr}"></div>'

    title_en_js = (
        f'if (isEn) document.title = "{_escape(location_name_en)} — Jeju 4·3 Story";'
        if location_name_en
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<script>
  // 메인 화면(index.html)과 같은 localStorage 키를 공유 — 이 페이지의 토글 버튼과
  // 메인 화면 토글이 서로 언어 설정을 이어받는다. 챗봇도 이 값을 읽어 같은 언어로 답한다.
  try {{ if (localStorage.getItem("jeju43-lang") === "en") document.documentElement.lang = "en"; }} catch (e) {{ /* 무시 */ }}
  function jeju43ToggleLang() {{
    try {{
      var cur = localStorage.getItem("jeju43-lang") === "en" ? "en" : "ko";
      localStorage.setItem("jeju43-lang", cur === "en" ? "ko" : "en");
    }} catch (e) {{ /* 무시 */ }}
    location.reload();
  }}
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(location_name_ko)} — 제주 4·3 스토리</title>
{internal_meta}
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700;900&display=swap">
<!-- design 파일 분리(spec.md 4.3) — 이 파일을 교체하면 전체 페이지 톤이 바뀐다 -->
<link rel="stylesheet" href="../design/archive.css">
</head>
<body>
<article class="story-page" data-location-id="{_escape(location_id)}">

  <nav class="story-nav" aria-label="이동">
    <a href="../index.html"><span aria-hidden="true">←</span> <span class="lang-ko-inline">지도로 돌아가기</span><span class="lang-en-inline" lang="en">Back to map</span></a>
    <button type="button" class="lang-toggle-btn" onclick="jeju43ToggleLang()" id="langToggleBtn">EN</button>
  </nav>
  <script>(function () {{
    var isEn = document.documentElement.lang === "en";
    var b = document.getElementById("langToggleBtn");
    if (b) b.textContent = isEn ? "KO" : "EN";
    {title_en_js}
  }})();</script>

  {hero_html}

  {intro_section}

  {dev_section}

  {conflicts_html}

  {timeline_html}

  {closing_section}

  {visuals_html}

  {audio_html}

  {quiz_html}

  {sources_html}
  {unmatched_marker}

  <div id="chatbot-modal" data-kb-source="07"></div>
  <script src="{_escape(chatbot_modal_relpath)}"></script>
{quiz_script}

</article>
</body>
</html>
"""


def sync_to_supabase(location_id: str, detail_html: str, map_html: str) -> None:
    """Supabase locations 테이블(location_id, detail_html, map_html, updated_at)에 upsert한다.

    이 테이블은 팀·함께공 전용 비공개 미리보기(Next.js /api/preview/*, 비밀번호 게이트
    뒤)가 읽는 유일한 소스다 — 브라우저는 anon key로 이 테이블에 절대 직접 닿지 않는다.

    SUPABASE_URL(또는 NEXT_PUBLIC_SUPABASE_URL)·SUPABASE_SERVICE_ROLE_KEY가 없으면
    로컬 개발/오프라인 실행을 막지 않도록 경고만 남기고 조용히 건너뛴다. 반면 키가 있는데
    실제 HTTP 호출이 실패하면(네트워크·인증 오류 등) 그건 감춰서는 안 되는 진짜 실패이므로
    그대로 예외를 올린다.
    """
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.warning(
            "SUPABASE_URL(또는 NEXT_PUBLIC_SUPABASE_URL)/SUPABASE_SERVICE_ROLE_KEY가 없어 "
            "'%s'의 Supabase 동기화를 건너뜁니다.",
            location_id,
        )
        return

    import httpx

    payload = {
        "location_id": location_id,
        "detail_html": detail_html,
        "map_html": map_html,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    response = httpx.post(
        f"{url.rstrip('/')}/rest/v1/locations",
        json=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    logger.info("Supabase locations 테이블에 '%s' upsert 완료", location_id)
