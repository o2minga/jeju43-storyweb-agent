/*
 * 07-chatbot — 자기완결 모달 스크립트 (neobeunsungi)
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
        { qa_id: "kb-01", question: "너븐숭이 4·3기념관은 어떤 곳인가요?", answer: "2009년 조성된 추모공원으로 위령비·기념관·방사탑을 갖추고 있으며, 1949년 1월 17일 북촌주민이 희생된 장소 중 하나이자 소설 『순이삼촌』의 배경이 된 곳입니다.", source: "너븐숭이 4·3유적지 안내판(N-1)" },
        { qa_id: "kb-02", question: "북촌대학살(1949.1.17)은 왜 일어났나요?", answer: "너븐숭이 고갯길 군인 2명 무장대 습격 사망 → 함덕 2연대 3대대 보복 → 마을 방화·학교 집결 후 분산 총살.", source: "현장 안내판·추념비·제주4·3사건일지" },
        { qa_id: "kb-03", question: "희생자는 몇 명인가요?", answer: "하나로 단정할 수 없습니다. 당일 300여 명(학교 주변), 이튿날까지 400명 가량(사건일지·너븐숭이 안내판), 행방불명 포함 전체 434명(추념비)이라는 기록이 함께 있습니다.", source: "현장 안내판·추념비·제주4·3사건일지" },
        { qa_id: "kb-04", question: "애기무덤에는 왜 아이들 무덤만 있나요?", answer: "어른 시신은 survivors가 다른 곳에 안장, 아이들은 임시 매장 그대로 70년. 20여 기 중 최소 8기 이상이 대학살 희생 아동입니다.", source: "애기무덤 안내판(N-3)" },
        { qa_id: "kb-05", question: "『순이삼촌』은 어떤 소설인가요?", answer: "현기영(1978), 4·3 참혹함과 후유증 고발, 묻혀 있던 진실을 문학으로 공론화. 2008년 정부 옴팡밭 매입 후 문학비 건립.", source: "순이삼촌 문학비 안내판(N-4)" },
        { qa_id: "kb-06", question: "옴팡밭의 시신 묘사를 더 자세히 알 수 있나요?", answer: "옴팡밭 안내판(N-5)의 원문 표현만 인용할 수 있으며, 이를 바탕으로 장면을 확장하거나 재현하지는 않습니다.", source: "옴팡밭 안내판(N-5)" },
        { qa_id: "kb-07", question: "당팟과 너븐숭이는 어떻게 다른가요?", answer: "당팟은 북촌국민학교 동쪽 학살터(100여 명 희생), 너븐숭이/옴팡밭은 서쪽 학살터입니다.", source: "당팟 안내판(N-6)·북촌마을 안내판(N-2)" },
        { qa_id: "kb-08", question: "북촌초등학교는 당시 어떤 일을 겪었나요?", answer: "1949.1.10 폐교(개교 7년 만), 주민 집결·1차 총살 장소. 5개월 후 마을 복구, 2년 9개월 후 학교 재건, 재학생 216명 53년 만에 명예졸업장.", source: "북촌초등학교 추념비(N-7)" },
        { qa_id: "kb-09", question: "정지퐁낭은 어떤 나무인가요?", answer: "당팟 인근 800년 된 팽나무. 1958년 태풍 '사라'로 쓰러졌다가 다시 심음. 옆 제주목사 선정비에 4·3 총탄 자국 선명.", source: "정지퐁낭 기념비(N-8)" }
      ],
      FACTS: [
        { id: "f-01", text: "너븐숭이 4·3기념관(본체)은 조천읍 북촌3길 3(북위 33.545959, 동경 126.688749)에 있으며, 2009년 조성된 추모공원으로 위령비·기념관·방사탑을 갖추고 있다.", source: "안내판 조사보고서 현장 기록", hint: "너븐숭이 4·3기념관은 어디에 있나요?" },
        { id: "f-02", text: "이 유적군에는 본체 외에 애기무덤, 순이삼촌 문학비·옴팡밭, 당팟, 북촌초등학교 추념비, 정지퐁낭 기념비가 연계 지점으로 포함된다.", source: "안내판 조사보고서 현장 기록", hint: "이 유적군에는 어떤 연계 지점들이 있나요?" },
        { id: "f-03", text: "올레 19코스는 소설 『순이삼촌』의 배경인 북촌리 학살 현장과 애기무덤이 위치한 핵심 코스로 이 유적군을 지난다.", source: "올레길 × 4·3 유적지 코스별 안내", hint: "올레길과는 어떤 관계가 있나요?" },
        { id: "f-04", text: "북촌은 포구를 중심으로 '본동', 서쪽 서우봉과 접한 '해동', 남쪽 중산간 방향의 '억수동', 1990년대 조성된 '한사동'까지 네 개의 자연마을로 이루어져 있다.", source: "현장 안내판(북촌마을 안내판, N-2)", hint: "북촌마을은 어떻게 구성되어 있나요?" },
        { id: "f-05", text: "1947년 8월 13일, 삐라를 붙이던 주민들을 향해 경찰이 발포해 3명이 부상당했다.", source: "제주4·3사건일지·현장 안내판", hint: "1947년 8월에 무슨 일이 있었나요?" },
        { id: "f-06", text: "1948년 4월 21일 무장대가 북촌리 선거관리위원회 사무소를 공격해 선거기록을 탈취했고, 6월 16일에는 북촌포구에서 우도지서 경찰관 2명이 무장대에게 살해되었다.", source: "현장 안내판", hint: "1948년에는 어떤 사건들이 있었나요?" },
        { id: "f-07", text: "1948년 12월 16일, 마을을 지키며 토벌대에 협조하던 민보단원 24명이 구좌읍 동복리 '낸시빌레'에서 군인들에게 집단총살되었다.", source: "현장 안내판", hint: "낸시빌레에서는 무슨 일이 있었나요?" },
        { id: "f-08", text: "1949년 1월 10일, 북촌국민학교가 개교 7년 만에 폐교되었다.", source: "추념비(2013)", hint: "북촌국민학교는 언제 폐교되었나요?" },
        { id: "f-09", text: "1949년 1월 17일 새벽, 너븐숭이 고갯길에서 군인 2명이 무장대의 습격으로 숨지자, 함덕 주둔 2연대 3대대가 보복에 나서 마을에 불을 지르고 주민들을 북촌국민학교 운동장에 집결시켰다.", source: "현장 안내판·추념비·제주4·3사건일지", hint: "북촌대학살은 어떻게 벌어졌나요?" },
        { id: "f-10", text: "북촌대학살 희생자 수는 세는 기준에 따라 다르게 기록되어 있다 — 당일 300여 명, 이튿날까지 400명 가량, 행방불명 포함 전체 434명이다.", source: "현장 안내판·추념비·제주4·3사건일지", hint: "희생자는 몇 명인가요?" },
        { id: "f-11", text: "살아남은 주민들은 함덕으로 소개되었고, 5개월 만에 마을을 복구했으며, 2년 9개월 만에 학교가 재건되었다. 폐교 당시 재학생 216명은 53년 만에 명예졸업장을 받았다.", source: "추념비(2013)", hint: "생존 주민들은 이후 어떻게 되었나요?" },
        { id: "f-12", text: "1954년 1월, 북촌국민학교에서 이른바 '아이고 사건'이 있었으며 이후에도 주민들에 대한 국가의 억압이 지속되었다.", source: "안내판 조사보고서(문제점 서술)", hint: "'아이고 사건'은 무엇인가요?" },
        { id: "f-13", text: "애기무덤에는 20여 기의 아이들 무덤이 모여 있으며, 적어도 8기 이상은 북촌대학살 때 희생된 어린아이의 무덤이다. 어른들의 시신은 다른 곳에 안장되었으나, 아이들의 시신은 임시 매장한 상태 그대로 남아 있다.", source: "애기무덤 안내판(N-3)", hint: "애기무덤에는 왜 아이들 무덤만 있나요?" },
        { id: "f-14", text: "소설 『순이삼촌』(현기영, 1978)은 4·3사건의 참혹함과 후유증을 고발하고 진실을 문학으로 공론화했다. 2008년 정부가 옴팡밭 부지를 매입해 문학비를 세웠다.", source: "순이삼촌 문학비 안내판(N-4)", hint: "『순이삼촌』은 어떤 소설인가요?" },
        { id: "f-15", text: "정지퐁낭(약 800년 된 팽나무) 옆 제주목사 선정비에는 4·3 당시 총탄 자국이 선명하게 남아 있다.", source: "정지퐁낭 기념비(N-8)·안내판 조사보고서 지적", hint: "정지퐁낭에는 어떤 흔적이 남아있나요?" },
        { id: "f-16", text: "북촌초등학교 추념비는 2013년 10월 27일 건립되었으며, 뒷면에 폐교→함덕 소개→마을 복구→학교 재건→명예졸업장 216명이라는 시간축이 기록되어 있다.", source: "북촌초등학교 추념비(N-7)", hint: "북촌초등학교 추념비에는 무엇이 기록되어 있나요?" },
        { id: "f-17", text: "너븐숭이 4·3기념관은 소설 『순이삼촌』의 배경이 된 장소로 알려져 있으며, 2009년 위령비·기념관·방사탑을 갖춘 추모공원으로 조성되었다.", source: "너븐숭이 4·3유적지 안내판(N-1)", hint: "너븐숭이 4·3기념관은 어떤 곳인가요?" }
      ],
      QUOTES: [
        { id: "q-01", text: "조천면 북촌리에서 경찰이 삐라를 붙이는 소년을 추격하는 과정에서 발포해 주민 3명에 총상", source: "제주4·3사건일지 (1947-08-13)" },
        { id: "q-02", text: "'북촌사건' 발생. 토벌대, 마을 인근에서 군인들이 기습받은데 대한 보복으로 조천면 북촌리를 모두 불태우고 이튿날까지 주민 400명 가량을 집단총살", source: "제주4·3사건일지 (1949-01-17)" },
        { id: "q-03", text: "'북촌 학살사건' 발생", source: "한눈에 보는 4·3 (1949-01-17)" },
        { id: "q-04", text: "너븐숭이 4·3유적지는 1949년 1월 17일 북촌주민 400여 명이 희생된 장소 중 하나이며, 4·3의 아픔을 알리는 소설 \"순이삼촌\"의 배경이 된 장소이기도 합니다.", source: "너븐숭이 4·3유적지 안내판(N-1)" },
        { id: "q-05", text: "1949년 1월 17일 너븐숭이 인근에서 군인 2명이 무장대의 습격으로 숨지자 북촌초등학교 주변 들과 밭에서 북촌주민 3백여 명이 집단학살 당하는 등 북촌마을은 4·3사건 최대의 피해마을 중 하나이다.", source: "북촌마을 안내판(N-2)" },
        { id: "q-06", text: "북촌리 주민 학살 사건 때 어른들의 시신은 살아남은 사람들에 의해 다른 곳에 안장 되었으나 어린아이들의 시신은 임시 매장한 상태 그대로 지금까지 남아있다. 현재 20여 기의 애기무덤이 모여 있는데 적어도 8기 이상은 북촌대학살 때 희생된 어린아이의 무덤이다.", source: "애기무덤 안내판(N-3)" },
        { id: "q-07", text: "현기영은 소설 '순이삼촌'을 통해 4·3사건의 참혹상과 그 후유증을 고발함과 동시에 오랫동안 묻혀 있던 사건의 진실을 문학을 통해 공론화시켰다.", source: "순이삼촌 문학비 안내판(N-4)" },
        { id: "q-08", text: "'옴팡밭'은 '오목하게 쏙 들어가 있는 밭'이라는 뜻이다. 4·3 사건 당시 최대의 인명피해로 기록되고 있는 1949년 1월 17일 북촌대학살 현장의 한 곳이다.", source: "옴팡밭 안내판(N-5)" },
        { id: "q-09", text: "당팟(4·3희생터) — 북촌학살은 북촌국민학교를 중심으로 동쪽의 '당팟'과 서쪽의 '너븐숭이'로 나누어 이루어졌고 이곳 '당팟'에서는 100여 명이 희생되었다.", source: "당팟 안내판(N-6)" },
        { id: "q-10", text: "이곳은 제주4·3의 최대 희생지인 북촌리민 대참사(大慘死)의 현장이다. 전 가옥이 소실(燒失)되고 가족이 흩어져 행방불명이 되니 전체 희생자는 434명이나 되었다.", source: "북촌초등학교 추념비(N-7, 2013)" },
        { id: "q-11", text: "정지퐁낭은 수령 약 800년 된 팽나무로 마을의 정자 역할을 하였으나 1958년 9월 태풍 '사라'호에 의해 한쪽으로 쓰러지자 제거하고 다시 심었다. 이 나무 옆에 있는 제주목사 선정비에는 4·3사건 당시 총탄자국들이 선명히 남아 있다.", source: "정지퐁낭 기념비(N-8)" }
      ],
      REFUSE_KEYWORDS: ["무장대 탓", "군 탓", "탓인가요", "책임 소재", "이름을", "실명", "성함"],
      FALLBACK: "기록에 명시되지 않은 내용입니다."
    },
    en: {
      KB: [
        { qa_id: "kb-01", question: "What kind of place is the Neobeunsungi 4·3 Memorial Hall?", answer: "It is a memorial park built in 2009, with a memorial monument, an exhibition hall, and a stone tower. It is one of the sites where Bukchon residents were killed on January 17, 1949, and the setting for the novel Aunt Suni.", source: "Neobeunsungi 4·3 Heritage Site information board (N-1)" },
        { qa_id: "kb-02", question: "Why did the Bukchon Massacre (Jan 17, 1949) happen?", answer: "After two soldiers were killed in an ambush by an armed group on the Neobeunsungi hill road, the 3rd Battalion, 2nd Regiment stationed in Hamdeok retaliated, burning the village, gathering residents at the school, and shooting them in separate groups.", source: "On-site information board · memorial · Jeju 4·3 Incident Chronicle" },
        { qa_id: "kb-03", question: "How many people were killed?", answer: "This cannot be reduced to a single figure. Records show about 300 that day (near the school), around 400 by the next day (Incident Chronicle · Neobeunsungi board), and 434 in total including the missing (memorial monument).", source: "On-site information board · memorial · Jeju 4·3 Incident Chronicle" },
        { qa_id: "kb-04", question: "Why does the children's grave site hold only children's graves?", answer: "The bodies of adults were reburied elsewhere by survivors, but children's bodies have remained where they were temporarily buried for nearly 70 years. At least 8 of the roughly 20 graves belong to children killed in the massacre.", source: "Children's grave information board (N-3)" },
        { qa_id: "kb-05", question: "What kind of novel is Aunt Suni?", answer: "Written by Hyun Ki-young in 1978, it exposed the brutality and aftermath of 4·3 and brought the buried truth into public discussion through literature. In 2008 the government purchased land at Ompangbat and erected a literary monument there.", source: "Aunt Suni Literary Monument board (N-4)" },
        { qa_id: "kb-06", question: "Can you describe in more detail what happened to the bodies at Ompangbat?", answer: "Only the original wording of the Ompangbat information board (N-5) can be quoted; this page does not expand on or reenact the scene.", source: "Ompangbat information board (N-5)" },
        { qa_id: "kb-07", question: "What is the difference between Dangpat and Neobeunsungi?", answer: "Dangpat is the massacre site to the east of Bukchon Elementary School (about 100 killed), while Neobeunsungi/Ompangbat is the site to the west.", source: "Dangpat board (N-6) · Bukchon Village board (N-2)" },
        { qa_id: "kb-08", question: "What happened to Bukchon Elementary School at the time?", answer: "It closed on January 10, 1949, just seven years after opening, and was the site where residents were gathered before the first round of shootings. The village was rebuilt after 5 months, the school reopened after 2 years and 9 months, and the 216 enrolled students received honorary diplomas 53 years later.", source: "Bukchon Elementary School memorial (N-7)" },
        { qa_id: "kb-09", question: "What is the Jeongjipongnang tree?", answer: "It is a roughly 800-year-old hackberry tree near Dangpat, which fell during Typhoon Sarah in 1958 and was replanted. The nearby monument to a Joseon-era magistrate still clearly bears bullet marks from 4·3.", source: "Jeongjipongnang monument (N-8)" }
      ],
      FACTS: [
        { id: "f-01", text: "The Neobeunsungi 4·3 Memorial Hall (main site) is located at Bukchon 3-gil 3, Jocheon-eup (33.545959°N, 126.688749°E), a memorial park built in 2009 with a monument, exhibition hall, and stone tower.", source: "Survey report field records", hint: "Where is the Neobeunsungi 4·3 Memorial Hall?" },
        { id: "f-02", text: "Beyond the main site, this heritage cluster includes the children's graves, the Aunt Suni Literary Monument and Ompangbat, Dangpat, the Bukchon Elementary School memorial, and the Jeongjipongnang monument.", source: "Survey report field records", hint: "What connected sites are part of this cluster?" },
        { id: "f-03", text: "Olle Trail Course 19 passes through this heritage cluster, including the Bukchon massacre site and the children's graves that are the setting for the novel Aunt Suni.", source: "Olle Trail × 4·3 heritage site course guide", hint: "How is this connected to the Olle trail?" },
        { id: "f-04", text: "Bukchon is made up of four natural hamlets centered on its harbor: Bondong, Haedong bordering Seoubong to the west, Eoksu-dong toward the inland hills to the south, and Hansa-dong, newly formed in the 1990s.", source: "On-site information board (Bukchon Village board, N-2)", hint: "How is Bukchon Village made up?" },
        { id: "f-05", text: "On August 13, 1947, police opened fire on villagers who were putting up leaflets, injuring three.", source: "Jeju 4·3 Incident Chronicle · on-site board", hint: "What happened in August 1947?" },
        { id: "f-06", text: "On April 21, 1948, an armed group attacked the Bukchon-ri election office and seized the election records; on June 16, two police officers from the Udo substation were killed by an armed group at Bukchon harbor.", source: "On-site information board", hint: "What incidents happened in 1948?" },
        { id: "f-07", text: "On December 16, 1948, 24 members of the local defense corps who had cooperated with the suppression forces while guarding the village were shot to death by soldiers at 'Naensibille' in Dongbok-ri, Gujwa-eup.", source: "On-site information board", hint: "What happened at Naensibille?" },
        { id: "f-08", text: "On January 10, 1949, Bukchon Elementary School closed, just seven years after it opened.", source: "Memorial (2013)", hint: "When did Bukchon Elementary School close?" },
        { id: "f-09", text: "Before dawn on January 17, 1949, two soldiers were killed in an ambush by an armed group on the Neobeunsungi hill road; soldiers of the 3rd Battalion, 2nd Regiment stationed in Hamdeok retaliated by burning the village and gathering residents in the schoolyard of Bukchon Elementary School.", source: "On-site information board · memorial · Jeju 4·3 Incident Chronicle", hint: "How did the Bukchon Massacre unfold?" },
        { id: "f-10", text: "The number of victims of the Bukchon Massacre is recorded differently depending on the scope counted — about 300 that day, around 400 by the next day, and 434 in total including the missing.", source: "On-site information board · memorial · Jeju 4·3 Incident Chronicle", hint: "How many people were killed?" },
        { id: "f-11", text: "Survivors were evacuated to Hamdeok, rebuilt the village within 5 months, and reopened the school after 2 years and 9 months. The 216 students enrolled at closure received honorary diplomas 53 years later.", source: "Memorial (2013)", hint: "What happened to survivors afterward?" },
        { id: "f-12", text: "In January 1954, the so-called 'Aigo Incident' occurred at Bukchon Elementary School, and repression of villagers by the state continued afterward.", source: "Survey report (noted issue)", hint: "What was the 'Aigo Incident'?" },
        { id: "f-13", text: "The children's graves hold about 20 burial mounds, at least 8 of which belong to children killed in the Bukchon massacre. Adults' bodies were reburied elsewhere, but children's bodies remained as temporarily buried.", source: "Children's grave information board (N-3)", hint: "Why does the children's grave site hold only children's graves?" },
        { id: "f-14", text: "The novel Aunt Suni (Hyun Ki-young, 1978) exposed the brutality and aftermath of 4·3 and brought the truth into public discussion through literature. In 2008 the government purchased land at Ompangbat and erected a literary monument.", source: "Aunt Suni Literary Monument board (N-4)", hint: "What kind of novel is Aunt Suni?" },
        { id: "f-15", text: "Beside Jeongjipongnang (a roughly 800-year-old hackberry tree), a monument to a Joseon-era magistrate still clearly bears bullet marks from 4·3.", source: "Jeongjipongnang monument (N-8) · survey report note", hint: "What traces remain at Jeongjipongnang?" },
        { id: "f-16", text: "The Bukchon Elementary School memorial was erected on October 27, 2013, recording on its back a timeline from closure to evacuation, village rebuilding, school reconstruction, and the 216 honorary diplomas.", source: "Bukchon Elementary School memorial (N-7)", hint: "What does the Bukchon Elementary School memorial record?" },
        { id: "f-17", text: "The Neobeunsungi 4·3 Memorial Hall is known as the setting for the novel Aunt Suni, and was built in 2009 as a memorial park with a monument, exhibition hall, and stone tower.", source: "Neobeunsungi 4·3 Heritage Site board (N-1)", hint: "What kind of place is the Neobeunsungi 4·3 Memorial Hall?" }
      ],
      QUOTES: [
        { id: "q-01", text: "Police fired on a boy putting up leaflets in Bukchon-ri, Jocheon-myeon, injuring 3 residents.", source: "Jeju 4·3 Incident Chronicle (1947-08-13) [translated]" },
        { id: "q-02", text: "The 'Bukchon Incident' occurred. Suppression forces, in retaliation for an ambush on soldiers near the village, burned down all of Bukchon-ri, Jocheon-myeon, and massacred about 400 residents by the next day.", source: "Jeju 4·3 Incident Chronicle (1949-01-17) [translated]" },
        { id: "q-03", text: "The 'Bukchon Massacre' occurred.", source: "Jeju 4·3 at a Glance (1949-01-17) [translated]" },
        { id: "q-04", text: "Neobeunsungi is the Jeju April 3rd historic site where around 400 Bukchon villagers were killed on 17th January 1949. This place is also the location where the novel Aunt Suni is based.", source: "Neobeunsungi 4·3 Heritage Site board (N-1) [translated]" },
        { id: "q-05", text: "When two soldiers were killed near Neobeunsungi in an ambush by an armed group on January 17, 1949, about 300 Bukchon residents were massacred in the fields around Bukchon Elementary School — one of the villages hit hardest by 4·3.", source: "Bukchon Village board (N-2) [translated]" },
        { id: "q-06", text: "In the Bukchon-ri massacre, adults' bodies were reburied elsewhere by survivors, but children who were killed remained buried where they were temporarily interred. Today about 20 children's graves remain, at least 8 of them from the massacre.", source: "Children's grave information board (N-3) [translated]" },
        { id: "q-07", text: "Through the novel Aunt Suni, Hyun Ki-young exposed the brutality of 4·3 and its aftermath, and brought the long-buried truth of the incident into public discussion through literature.", source: "Aunt Suni Literary Monument board (N-4) [translated]" },
        { id: "q-08", text: "'Ompangbat' means a farming field with a concave surface. It is one of the sites of the Bukchon massacre on January 17, 1949, the deadliest single incident of the 4·3 period.", source: "Ompangbat information board (N-5) [translated]" },
        { id: "q-09", text: "Dangpat (4·3 sacrifice site) — the Bukchon massacre was carried out east at Dangpat and west at Neobeunsungi, centered on Bukchon Elementary School; about 100 people were killed at Dangpat.", source: "Dangpat information board (N-6) [translated]" },
        { id: "q-10", text: "This is the site of the greatest single tragedy of Jeju 4·3 among the Bukchon villagers. Every house was burned down and families were scattered and went missing, bringing the total number of victims to 434.", source: "Bukchon Elementary School memorial (N-7, 2013) [translated]" },
        { id: "q-11", text: "Jeongjipongnang is a roughly 800-year-old hackberry tree that served as the village's pavilion tree; it fell during Typhoon Sarah in September 1958 and was replanted. The nearby monument to a Joseon-era magistrate still clearly bears bullet marks from 4·3.", source: "Jeongjipongnang monument (N-8) [translated]" }
      ],
      REFUSE_KEYWORDS: ["armed group's fault", "military's fault", "whose fault", "who is responsible", "real name", "full name", "victim's name"],
      FALLBACK: "This is not specified in the record."
    }
  };

  var CHROME = {
    ko: {
      launcherLabel: "제주 4·3 안내 챗봇 열기",
      header: "제주 4·3 안내원",
      placeholder: "너븐숭이와 북촌에 대해 물어보세요",
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
      placeholder: "Ask about Neobeunsungi and Bukchon",
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

  function scoreEntry(haystackText, question) {
    var q = normalize(question);
    var h = normalize(haystackText);
    if (!h || !q) return 0;
    if (h.length >= 2 && (q.indexOf(h) !== -1 || h.indexOf(q) !== -1)) return 20;
    var shortStr = h.length <= q.length ? h : q;
    var longStr = h.length <= q.length ? q : h;
    var score = 0;
    var N = 3;
    if (shortStr.length >= N) {
      for (var j = 0; j <= shortStr.length - N; j++) {
        if (longStr.indexOf(shortStr.substring(j, j + N)) !== -1) score += 0.5;
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

  function followupPool() {
    var d = data();
    var pool = d.KB.map(function (e) { return { id: e.qa_id, question: e.question }; });
    pool = pool.concat(d.FACTS.map(function (e) { return { id: e.id, question: e.hint }; }));
    return pool;
  }

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

    var shownIds = {};

    function renderFollowups(container) {
      var c = CHROME[getLang()];
      var candidates = followupPool().filter(function (e) { return e.question && !shownIds[e.id]; });
      if (!candidates.length) return;
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
