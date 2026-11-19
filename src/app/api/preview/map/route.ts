import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

const COOKIE_NAME = "preview_auth";

export async function GET(request: NextRequest) {
  const password = process.env.PREVIEW_PASSWORD;
  const cookie = request.cookies.get(COOKIE_NAME)?.value;
  if (!password || cookie !== password) {
    return NextResponse.json({ error: "인증이 필요합니다." }, { status: 401 });
  }

  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from("locations")
    .select("map_html")
    .order("updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  if (!data) {
    return NextResponse.json({ error: "등록된 장소가 아직 없습니다." }, { status: 404 });
  }

  return new NextResponse(data.map_html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
