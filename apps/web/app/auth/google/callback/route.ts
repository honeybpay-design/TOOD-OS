import { NextRequest } from "next/server";
import { oauthCookie, pendingVerifier } from "@/lib/oauth-flow";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const verifier = pendingVerifier(request.cookies.get("__session")?.value);
  const fail = () => new Response(null, { status: 302, headers: {
    location: "/login", "cache-control": "no-store", "referrer-policy": "no-referrer",
    // No Set-Cookie on failure: a late response must not erase a newer login.
    // The existing pending verifier expires after its original ten-minute TTL.
  } });
  const apiUrl = process.env.API_URL;
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  if (!apiUrl || !verifier || !code || !state || request.nextUrl.searchParams.has("error")) return fail();
  try {
    const query = new URLSearchParams({ code, state });
    const upstream = await fetch(`${apiUrl}/v1/auth/google/callback?${query}`, {
      headers: { "x-oauth-verifier": verifier }, redirect: "error", cache: "no-store",
      signal: AbortSignal.timeout(20000),
    });
    if (!upstream.ok) return fail();
    const data = await upstream.json() as { session_token?: string };
    if (typeof data.session_token !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(data.session_token)) return fail();
    return new Response(null, { status: 302, headers: {
      location: "/dashboard", "set-cookie": oauthCookie(data.session_token, 30 * 24 * 60 * 60),
      "cache-control": "no-store", "referrer-policy": "no-referrer",
    } });
  } catch {
    return fail();
  }
}
