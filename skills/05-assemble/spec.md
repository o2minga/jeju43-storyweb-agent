# skills/05-assemble/spec.md — 05-assemble 스킬 상세 스펙 ‹조립공›

> 이 문서는 `AGENT-SPEC.md`의 일반 원칙 위에서 05-assemble만의 세부 규칙을 정의한다.
> **특정 유적지의 실제 내용은 예시로도 포함하지 않는다.** 아래 예시는 전부 플레이스홀더다.
> ⚠ 이 문서의 6번(출력 형식)은 08-review가 자동으로 검수할 수 있는지를 좌우한다. 태그·속성 규칙을 임의로 바꾸지 않는다.

---

## 0. 아키텍처 위치 (지금 단계)

`AGENT-SPEC.md` 5장 기준 **05-assemble은 C그룹(조립형)** 이다.

- Claude를 호출하지 않는다 — 01·02·03·04의 이미 검증된 JSON을 이 문서 5장의 마크업 규칙에 맞춰 정적 `.html`로 조립하는 **코드 템플릿**이다.
- 같은 입력이면 항상 같은 출력이 나와야 하는 반복성이 이 스킬의 핵심 존재 이유이므로, Claude 대신 코드로 처리한다.

---

## 1. 목표

02(이야기)·03(비주얼)·04(오디오)·07(챗봇)의 결과물을 받아, 브라우저에서 열리는 스토리 웹페이지(`.html`) 한 장으로 조립한다. **카드만 바꿔 넣으면 같은 품질의 페이지가 나오는 반복성**을 담보하는 자리다.

---

## 2. 입력

| 스텝 | 받는 것 | 없을 경우 처리 |
|---|---|---|
| 02 출력 | 원고, 출처, 타임라인, 언어 라벨, `forbidden_topics`, `conflicts_carried_forward`, `publication_flag` | 필수 — 없으면 조립 중단 |
| 03 출력 | 이미지·영상 경로 및 `[연출]` 여부 | **placeholder 단계일 수 있음** — placeholder면 해당 블록을 "준비 중" 상태로 표시하고 조립은 계속 진행 |
| 04 출력 | 오디오 경로, 싱크 타임라인 | **placeholder 단계일 수 있음** — 위와 동일 |
| 07 출력 | 챗봇 KB, 가드레일, 모달 스크립트 | 필수 — 없으면 챗봇 블록 자체를 생략 (에러 아님, 정상적인 블록 생략) |

> B그룹(03·04)이 아직 placeholder라는 이유로 05가 실패해서는 안 된다. 개발 초기엔 이게 정상 상태다.

---

## 3. 범위 (포함 / 제외)

**포함**
- 원고를 화면 구획에 배치
- 내용에 맞는 블록 선택·조립 (아래 4번 참고)
- 출처를 규칙대로 하단에 표기
- 사실 서술과 `[연출]` 표시를 구분해서 렌더링
- 인터랙티브 타임라인, AI 챗봇 모달 스크립트 연동
- `.html` 파일 출력

**제외**
- 이야기 창작(02), 이미지·영상 생성(03), 오디오 생성(04), 챗봇 스크립트 자체 개발(07)
- 여러 장소를 지도로 묶는 일 (06 담당)

---

## 4. 일반 처리 원칙

1. **기본 틀은 세로 스크롤형.** 블록(글·타임라인·인용·이미지·영상·오디오 플레이어·출처)을 내용에 맞게 골라 쌓는다.
2. **없는 요소의 블록은 자동 생략한다.** (예: 타임라인 데이터가 비어 있으면 타임라인 블록 자체를 만들지 않는다 — 빈 블록을 만들고 숨기는 방식이 아니라, 애초에 생성하지 않는다.)
3. **스타일은 별도 `design` 파일로 분리한다.** 색·폰트·모양을 이 파일이 결정하며, 파일 교체만으로 전체 톤이 바뀌어야 한다. `.html` 본문에 스타일을 직접 하드코딩하지 않는다.
   현재 기본(아카이브/기록보관소 톤) design 파일: `output/design/archive.css` (+ 캐노니컬 사본 `skills/05-assemble/design/archive.css`).
   `<head>`에는 `<link rel="stylesheet" href="../design/archive.css">`만 넣고, 새 장소 페이지도 이 파일을 그대로 재사용한다.
   페이지 맨 위 `<header class="story-hero">`에 03의 첫 이미지(`figure.ai-generated`)를 재사용한 히어로를 두면(마크업 예시는 `output/gwandeokjeong/05-assemble.html` 참고) design 파일의 `.story-hero`/`.hero-media` 규칙이 자동으로 큼직한 오프닝 비주얼을 만들어준다. `[연출]`/`AI 생성` 배지는 `figure.ai-generated`에 CSS `::before`로 자동 부착되므로 마크업에서 별도 배지 요소를 추가할 필요는 없다.
4. **`publication_flag.internal_only`가 `true`이면, 완성된 `.html`의 `<head>`에 아래 메타 태그를 반드시 삽입한다:**
   ```html
   <meta name="internal-only" content="true">
   ```
   이 태그는 08-review가 기계적으로 확인할 수 있는 유일한 방법이므로 누락하면 안 된다.

---

## 5. 출력 마크업 규칙 (⚠ 08-review가 이 규칙에 의존함)

08단계가 사람 손 없이 자동으로 점검하려면, 05가 만드는 `.html`이 **일관된 태그 구조**를 가져야 한다. 아래 규칙은 반드시 지킨다.

### 출처 표기
```html
<span class="fact" data-fact-id="{02의 fact_id 또는 sentence_id}" data-source="{출처명}">
  {문장 내용}
</span>
```

### AI 생성물 `[연출]` 표시
```html
<figure class="ai-generated" data-origin="ai">
  <img src="{경로}" alt="...">
  <figcaption>[연출] {설명}</figcaption>
</figure>
```
문헌 원본 이미지는 `class="ai-generated"`를 붙이지 않고 `data-origin="archive"`로 표기한다.

### 타임라인 항목
```html
<div class="timeline-event" data-event-id="{02의 event_id}">...</div>
```

### 챗봇 모달
```html
<div id="chatbot-modal" data-kb-source="07">...</div>
```

### 출처 하단 블록
```html
<footer class="sources">
  <ul>
    <li data-source-ref="{출처명}">{출처 전체 표기}</li>
  </ul>
</footer>
```

> 이 규칙에 없는 새로운 블록을 추가해야 한다면, 반드시 이 문서에 규칙을 먼저 추가한 뒤 구현한다. 문서에 없는 태그 구조로 조립하면 08이 검수를 못 하거나 잘못된 결과를 낸다.

---

## 6. 제약

- 조립 시점에 02·07 산출물은 반드시 준비되어 있어야 한다 (03·04는 placeholder 허용)
- 출처가 없는 사실 문장은 애초에 `fact` 태그로 감싸지 않고 조립하지 않는다 (출처 없이 화면에 노출되는 사실이 없어야 함)
- design 파일 없이 실행되면 기본 design(무채색 최소 스타일)으로 fallback

---

## 7. 성공 기준

- [ ] 카드만 바꿔 넣으면 다음 장소도 같은 품질의 페이지가 나온다 (반복성)
- [ ] 모든 사실 문장이 `data-source`를 가진 `fact` 태그로 감싸져 있다
- [ ] 모든 AI 생성 이미지·영상에 `[연출]` 캡션과 `class="ai-generated"`가 붙어 있다
- [ ] `publication_flag.internal_only`가 true인 경우 `<meta name="internal-only">`가 삽입되어 있다
- [ ] 03·04가 placeholder 상태여도 조립이 에러 없이 완료된다 (해당 블록은 "준비 중" 표시)
- [ ] design 파일 교체만으로 전체 톤이 바뀐다
- [ ] **(중요) 다른 유적지의 02·03·04·07 출력으로 실행해도 동일 기준을 만족한다**
