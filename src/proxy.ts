import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "preview_auth";

/**
 * 사이트 전체에 걸리는 단순 비밀번호 게이트 — 팀·함께공 전용 비공개 미리보기.
 * 정식 로그인/세션 시스템이 아니라, PREVIEW_PASSWORD 값 하나와 쿠키를 비교만 한다.
 *
 * 기본값은 "막혀 있음"이다: PREVIEW_PASSWORD가 설정 안 돼 있거나 쿠키가 안 맞으면
 * 무조건 /preview-login으로 보낸다 — 배포 환경변수 설정을 깜빡했다고 사이트가
 * 실수로 공개되는 일이 없도록 안전한 기본값을 우선한다.
 *
 * Next.js 16부터 이 파일 컨벤션의 이름이 middleware → proxy로 바뀌었다(같은 기능,
 * export 함수 이름만 다름) — 옛 middleware.ts는 deprecated 경고가 뜬다.
 */
export function proxy(request: NextRequest) {
  const password = process.env.PREVIEW_PASSWORD;
  const cookie = request.cookies.get(COOKIE_NAME)?.value;

  if (password && cookie === password) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/preview-login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|preview-login|api/preview-login).*)",
  ],
};
