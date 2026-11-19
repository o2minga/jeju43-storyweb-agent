import { createClient } from "@supabase/supabase-js";

/**
 * service_role 키 전용 클라이언트 — 반드시 서버 코드(Route Handler 등)에서만 import한다.
 * RLS를 우회하므로 locations 테이블처럼 공개 정책이 아예 없는 테이블도 읽고 쓸 수 있다.
 * 브라우저로 절대 넘어가면 안 된다("use client" 컴포넌트나 클라이언트 번들에서 import 금지).
 */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY가 설정되어 있지 않습니다.",
    );
  }
  return createClient(url, key, {
    auth: { persistSession: false },
  });
}
