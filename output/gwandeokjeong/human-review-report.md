# 사람 확인 보고서 — gwandeokjeong

## ⚠ 사람 확인 필요 (전체 판정: HOLD)

### 사람 확인이 필요한 항목 (2건)
- **지어내기 여부** — 1차 키워드 대조: forbidden_topics 3건(자료 밖 통설='무장대 지도자 시신 전시' 등, 어린아이의 생사, 발포 위치 단정)의 핵심 문구가 05-assemble.html 본문에 그대로 등장하지 않음 — fail 아님. 오히려 아이의 생사는 "그 뒤 어떻게 되었는지는 남아 있는 기록에 없습니다"로 명시적으로 비워 두고, 사망 6명은 "관덕정과 도립병원 앞"으로 병기하며 4명 즉사·2명 병원 사망까지 구분해 금지선을 지켰다. 다만 spec.md 4장 ③에 따라 pass로 끝내지 않는다 — story-development(5단락, 서술이 가장 구체적)와 story-closing 등에서 출처 태그 밖에 놓인 연결·해석 문장, 카드 근거를 넘는 현재 경관 서술이 확인되어 needs_human으로 분류하고 해당 구간을 아래에 남긴다.
- **용어 풀이 여부** — 용어 풀이 여부는 spec.md 규칙상 원칙적으로 항상 needs_human으로 분류함

### 규칙 위반(fail/blocked) 항목 (3건)
- **출처 누락 여부** (fail) — data-fact-id=dev-4: 01-verify.json의 verified_facts에 존재하지 않는 fact_id를 참조합니다.
- **사실 일치 여부** (fail) — data-fact-id=dev-4: 05-assemble.html이 01-verify.json에 없는 fact_id를 참조합니다.
- **AI 챗봇 지식베이스 일치 여부** (fail) — 07-chatbot.json > kb[qa_id=kb-01]: 가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.; 07-chatbot.json > kb[qa_id=kb-03]: 가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.; 07-chatbot.json > kb[qa_id=kb-04]: 가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.; 07-chatbot.json > kb[qa_id=kb-05]: 가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.; 07-chatbot.json > kb[qa_id=kb-07]: 가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.; 07-chatbot.json > kb[qa_id=kb-08]: 가드레일 테스트용 항목(note_for_07)이 07의 kb[]에 실제 답변 가능 항목으로 들어가 있습니다.

