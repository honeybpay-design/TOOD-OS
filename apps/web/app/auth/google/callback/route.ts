import { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/**
 * Google OAuth callback relay.
 *
 * The registered redirect URI is https://tood.uk/auth/google/callback, so Google
 * sends the browser here with `code` and `state`. We proxy those to the FastAPI
 * callback, which validates everything, creates the session, and responds with a
 * 302 to /dashboard together with a `Set-Cookie` for the HttpOnly `tood_session`
 * cookie (Domain=.tood.uk).
 *
 * The API runs on a different host (run.app) and cannot set a tood.uk cookie
 * directly in the browser, so we relay its Set-Cookie header onto our own redirect
 * response. Because this response is served from tood.uk, the browser accepts and
 * stores the cookie. The session token never appears in the URL or in JS.
 */
export async function GET(request: NextRequest) {
  // Forward the full query string Google sent us (code, state, error).
  const search = request.nextUrl.search; // "" or "?code=...&state=..."
  const backendUrl = `${API_URL}/v1/auth/google/callback${search}`;

  let apiResponse: Response;
  try {
    // `manual` keeps the 302 + Set-Cookie readable instead of following it.
    apiResponse = await fetch(backendUrl, { redirect: "manual" });
  } catch {
    return redirectTo("/login");
  }

  // The API issues a 302 to /dashboard along with the session Set-Cookie.
  // Any non-redirect (e.g. 400 on a bad/expired state) sends the user back to login.
  if (apiResponse.status !== 302 && apiResponse.status !== 301) {
    return redirectTo("/login");
  }

  const setCookies = apiResponse.headers.getSetCookie();
  if (setCookies.length === 0) {
    // No session cookie was issued — nothing to authenticate with.
    return redirectTo("/login");
  }

  const headers = new Headers();
  for (const cookie of setCookies) {
    headers.append("set-cookie", cookie);
  }
  headers.set("location", "/dashboard");

  return new Response(null, { status: 302, headers });
}

function redirectTo(path: string): Response {
  return new Response(null, { status: 302, headers: { location: path } });
}
