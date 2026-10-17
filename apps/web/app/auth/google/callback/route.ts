import { NextRequest, NextResponse } from 'next/server';

/**
 * Google OAuth callback handler.
 * Proxies to FastAPI, extracts session_token, saves it via HTML/JS
 * to sessionStorage, then redirects to /dashboard.
 */
export async function GET(request: NextRequest) {
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000';
  const search = request.nextUrl.search;
  const backendUrl = `${apiUrl}/v1/auth/google/callback${search}`;

  try {
    const resp = await fetch(backendUrl, { method: 'GET', redirect: 'manual' });

    if (resp.status === 302 || resp.status === 301) {
      const location = resp.headers.get('location') ?? '';
      let sessionToken = '';
      let redirectTo = '/dashboard';
      try {
        const url = new URL(location);
        sessionToken = url.searchParams.get('session_token') ?? '';
        redirectTo = url.pathname;
      } catch { /* ignore */ }

      if (sessionToken) {
        const html = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><script>
try{sessionStorage.setItem('tood_session',${JSON.stringify(sessionToken)});}catch(e){}
window.location.replace(${JSON.stringify(redirectTo)});
</script><p>Signing in…</p></body></html>`;
        return new NextResponse(html, { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' } });
      }
      return NextResponse.redirect(location, { status: 302 });
    }

    const text = await resp.text();
    return new NextResponse(`Sign-in failed: ${text}`, { status: resp.status });
  } catch (err) {
    console.error('OAuth callback error:', err);
    return new NextResponse('Sign-in failed. Please try again.', { status: 502 });
  }
}
