import { NextRequest, NextResponse } from 'next/server';

/**
 * Google OAuth callback handler.
 * Proxies the callback to the FastAPI backend and follows the redirect to /dashboard.
 */
export async function GET(request: NextRequest) {
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000';
  const search = request.nextUrl.search; // preserve all query params (code, state, iss, etc.)

  const backendUrl = `${apiUrl}/v1/auth/google/callback${search}`;

  try {
    const resp = await fetch(backendUrl, {
      method: 'GET',
      redirect: 'manual', // don't auto-follow — we need to relay the redirect
    });

    // Backend returns 302 redirect to /dashboard?session_token=...
    if (resp.status === 302 || resp.status === 301) {
      const location = resp.headers.get('location');
      if (location) {
        return NextResponse.redirect(location, { status: 302 });
      }
    }

    // If backend returned an error, show it
    const text = await resp.text();
    return new NextResponse(text, {
      status: resp.status,
      headers: { 'content-type': 'text/plain' },
    });
  } catch (err) {
    console.error('OAuth callback proxy error:', err);
    return new NextResponse('OAuth callback failed. Please try again.', { status: 502 });
  }
}
