import { NextRequest, NextResponse } from 'next/server';

/**
 * Route protection: presence check on the `alma_token` cookie only.
 * Real JWT verification happens in the backend on every API call — middleware
 * is just a UX gate so unauthenticated users never render attorney pages.
 */
export function middleware(request: NextRequest) {
  const hasToken = Boolean(request.cookies.get('alma_token')?.value);
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/leads') && !hasToken) {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Already logged in — no reason to see the login page again.
  if (pathname === '/login' && hasToken) {
    const leadsUrl = new URL('/leads', request.url);
    return NextResponse.redirect(leadsUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/leads/:path*', '/login'],
};
