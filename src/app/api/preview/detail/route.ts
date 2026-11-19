import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

const COOKIE_NAME = "preview_auth";

export async function GET(request: NextRequest) {
  // middleware가 이미 이 경로를 막지만, matcher 설정 실수에 대비해 여기서도 한 번 더 확인한다.
  const password = process.env.PREVIEW_PASSWORD;
  const cookie = request.cookies.get(COOKIE_NAME)?.value;
  if (!password || cookie !== password) {
    return NextResponse.json({ error: "인증이 필요합니다." }, { status: 401 });
  }

  const id = request.nextUrl.searchParams.get("id");
  if (!id) {
    return NextResponse.json({ error: "id 쿼리 파라미터가 필요합니다." }, { status: 400 });
  }

  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from("locations")
    .select("detail_html")
    .eq("location_id", id)
    .maybeSingle();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  if (!data) {
    return NextResponse.json({ error: `location_id '${id}'를 찾을 수 없습니다.` }, { status: 404 });
  }

  return new NextResponse(data.detail_html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
