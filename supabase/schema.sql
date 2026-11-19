-- 제주 4·3 스토리웹 — 팀·함께공 전용 비공개 미리보기용 스키마
--
-- 실행 방법: Supabase 프로젝트 대시보드 → SQL Editor → 이 파일 내용을 붙여넣고 실행.
-- (이 리포지토리에서 자동으로 실행되지 않는다 — 프로젝트를 만들고 나서 한 번만 돌리면 됨)
--
-- 이 테이블은 완전히 서버 전용이다: agent 파이프라인(05 스텝 완료 시)이 service_role
-- 키로 쓰고, Next.js Route Handler(/api/preview/*)가 service_role 키로 읽는다. 브라우저는
-- anon key로 이 테이블에 절대 직접 접근하지 않는다 — 접근은 항상 비밀번호 게이트가 걸린
-- Next.js API를 거친다. 그래서 anon/authenticated용 공개 SELECT 정책이 필요 없다.

create table if not exists public.locations (
  location_id text primary key,
  detail_html text not null default '',
  map_html text not null default '',
  updated_at timestamptz not null default now()
);

alter table public.locations enable row level security;
-- 의도적으로 policy를 하나도 만들지 않는다 — RLS만 켜두면 anon/authenticated는
-- 기본적으로 전부 거부되고, service_role 키는 RLS 자체를 우회하므로 영향 없다.

-- 추모의 마음(온라인 헌화·방명록) 페이지용 테이블.
--
-- locations와 반대로, 이 테이블은 방문자의 브라우저(output/memorial.html)가 anon key로
-- 직접 읽고 쓰는 진짜 공개 게시판이다. 그래서 "누구나 쓰기·읽기는 가능하되, 한 번 남긴
-- 글은 아무도(작성자 본인 포함) 고치거나 지울 수 없음"만 RLS로 허용한다 — update/delete
-- 정책은 의도적으로 만들지 않았다. char_length 체크는 페이지의 입력 글자 수 제한(이름 30자,
-- 메시지 100자)을 DB에서도 강제해, 폼을 거치지 않고 API를 직접 호출하는 경우를 막는다.
create table if not exists public.memorial_messages (
  id bigint generated always as identity primary key,
  author text not null check (char_length(author) between 1 and 30),
  message text not null check (char_length(message) between 1 and 100),
  created_at timestamptz not null default now()
);

alter table public.memorial_messages enable row level security;

-- create policy는 create table과 달리 if not exists가 없어 재실행하면 에러가 난다.
-- drop 후 create로 감싸서, 이 파일을 몇 번을 다시 돌려도 안전하게(idempotent) 만든다.
drop policy if exists "memorial_messages_public_read" on public.memorial_messages;
create policy "memorial_messages_public_read"
  on public.memorial_messages for select
  to anon, authenticated
  using (true);

drop policy if exists "memorial_messages_public_insert" on public.memorial_messages;
create policy "memorial_messages_public_insert"
  on public.memorial_messages for insert
  to anon, authenticated
  with check (true);
