import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

// Force dynamic rendering — this route handles OAuth callbacks and must never
// be statically pre-rendered. API_URL is only available at runtime.
export const dynamic = "force-dynamic";

/**
 * Google OAuth callback relay.
 *
 * The registered redirect URI is https://tood.uk/auth/google/callback, so
 * Google sends the browser here with `code` and `state`. We proxy those to
 * the FastAPI callback, which validates everything, creates the session, and
 * responds with a 302 + Set-Cookie for the HttpOnly `tood_session` cookie.
 *
 * Instead of relaying the raw Set-Cookie header (which Node/Next strips from
 * 3xx fetch responses), we parse the token value out of the header string and
 * set the cookie natively via next/headers cookies().set(). Next.js merges
 * this into the outgoing 302 response so the browser receives it correctly.
 */
export async function GET(request: NextRequest) {
  const API_URL = process.env.API_URL;
  if (!API_URL) {
    console.error("[callback] API_URL env var is missing");
    return redirectTo("/login");
  }

  const search = request.nextUrl.search;
  const backendUrl = `${API_URL}/v1/auth/google/callback${search}`;

  let apiResponse: Response;
  try {
    apiResponse = await fetch(backendUrl, { redirect: "manual" });
  } catch (err) {
    console.error("[callback] fetch to API failed:", err);
    return redirectTo("/login");
  }

  console.log("[callback] API status:", apiResponse.status);

  if (apiResponse.status !== 302 && apiResponse.status !== 301) {
    console.error("[callback] unexpected API status:", apiResponse.status);
    return redirectTo("/login");
  }

  // Try getSetCookie() (Node 18+) first, then fall back to the raw header.
  // On 3xx responses the runtime may return [] from getSetCookie() even when
  // the header exists, so we always also check the raw value.
  const rawHeader: string =
    (typeof (apiResponse.headers as { getSetCookie?: () => string[] }).getSetCookie === "function"
      ? apiResponse.headers.getSetCookie().join(", ")
      : null) ??
    apiResponse.headers.get("set-cookie") ??
    "";

  console.log("[callback] raw set-cookie header present:", rawHeader.length > 0);

  // Parse: tood_session=<token>; Path=/; HttpOnly; ...
  // We need only the token value — everything after the first `=` up to the
  // first `;` or end of string, scoped to the tood_session key.
  const tokenMatch = rawHeader.match(/(?:^|,\s*)tood_session=([^;,]+)/i);
  const sessionToken = tokenMatch?.[1]?.trim() ?? null;

  console.log("[callback] sessionToken parsed:", sessionToken !== null);

  if (!sessionToken) {
    console.error("[callback] tood_session token not found in set-cookie header");
    return redirectTo("/login");
  }

  // Set cookie via Next.js cookies() API — this runs server-side in the
  // Cloud Run container (not through Firebase CDN), so Set-Cookie reaches
  // the browser directly on the 200 response below.
  const cookieStore = await cookies();
  cookieStore.set("tood_session", sessionToken, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 30 * 24 * 60 * 60,
    path: "/",
  });

  // Return a 200 HTML page that immediately redirects to /dashboard.
  // Using 200 (not 302) because Firebase CDN strips Set-Cookie on 3xx responses.
  // The cookie is set on this 200 response by Next.js before the JS redirect fires.
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? "tood.uk";
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const dashboardUrl = `${proto}://${host}/dashboard`;

  const response = new NextResponse(
    `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>window.location.replace(${JSON.stringify(dashboardUrl)});</script>
<p>Signing in…</p></body></html>`,
    { status: 200, headers: { "content-type": "text/html; charset=utf-8" } }
  );

  response.cookies.set("tood_session", sessionToken, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 30 * 24 * 60 * 60,
    path: "/",
  });

  return response;
}

function redirectTo(path: string): Response {
  return new Response(null, { status: 302, headers: { location: path } });
}
