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
    // The API did not issue a session cookie — fall back to login.
    // This should not happen in normal flow; indicates an API-side problem.
    console.error("[callback] tood_session token not found in set-cookie header");
    return redirectTo("/login");
  }

  // Set the cookie natively so Next.js sends it in the outgoing response.
  // cookies().set() is supported in Route Handlers per Next.js 16 docs.
  const cookieStore = await cookies();
  cookieStore.set("tood_session", sessionToken, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 30 * 24 * 60 * 60, // 30 days, matching the API
    path: "/",
  });

  // NextResponse.redirect returns a 307 by default; pass status 302 to
  // preserve the original flow. Next.js merges the cookie store into this
  // response's headers automatically.
  return NextResponse.redirect(new URL("/dashboard", request.url), { status: 302 });
}

function redirectTo(path: string): Response {
  return new Response(null, { status: 302, headers: { location: path } });
}
