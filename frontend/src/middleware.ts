import { NextRequest, NextResponse } from "next/server";

/**
 * Client-IP-Header für API-Rewrite zur FastAPI bewahren.
 * Reverse proxy should set X-Real-IP / X-Forwarded-For — forward to the API for client-IP detection.
 */
export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  const forwarded = request.headers.get("x-forwarded-for");
  const realIp = request.headers.get("x-real-ip");

  if (forwarded) {
    requestHeaders.set("x-forwarded-for", forwarded);
  }
  if (realIp) {
    requestHeaders.set("x-real-ip", realIp);
  }

  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: "/api/:path*",
};
