import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "preview_auth";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30일

export async function POST(request: NextRequest) {
  const password = process.env.PREVIEW_PASSWORD;
  if (!password) {
    return NextResponse.json(
      { error: "PREVIEW_PASSWORD가 서버에 설정되어 있지 않습니다." },
      { status: 500 },
    );
  }

  let body: { password?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "잘못된 요청입니다." }, { status: 400 });
  }

  if (body.password !== password) {
    return NextResponse.json({ error: "비밀번호가 올바르지 않습니다." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, password, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: MAX_AGE_SECONDS,
  });
  return response;
}
