import { cookies } from "next/headers";

/**
 * Base URL of the FastAPI backend. On Cloud Run this is provided via the
 * `API_URL` environment variable; locally it falls back to the dev API.
 */
const API_URL = process.env.API_URL ?? "http://localhost:8000";

type AuthMode = "session" | "bearer";

/**
 * Read the HttpOnly `tood_session` cookie server-side and proxy the request to
 * the FastAPI API, attaching the session token in the header the API expects:
 *  - "session" -> `X-Session-Token`  (data endpoints, app.core.auth.authenticate)
 *  - "bearer"  -> `Authorization: Bearer`  (OAuth endpoints in routes_oauth.py)
 *
 * The session token never reaches the browser, so this keeps the cookie
 * HttpOnly end-to-end while still letting the client dashboard call the API.
 */
export async function proxyToApi(
  path: string,
  request: Request,
  authMode: AuthMode = "session",
): Promise<Response> {
  const cookieStore = await cookies();
  const token = cookieStore.get("tood_session")?.value;

  if (!token) {
    // No session cookie -> tell the client to go back to login.
    return new Response(JSON.stringify({ detail: "not authenticated" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const headers: Record<string, string> =
    authMode === "bearer"
      ? { authorization: `Bearer ${token}` }
      : { "x-session-token": token };

  const init: RequestInit = { method: request.method, headers };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
    const contentType = request.headers.get("content-type");
    if (contentType) headers["content-type"] = contentType;
  }

  const upstream = await fetch(`${API_URL}/v1/${path}`, init);

  // Relay the upstream status and body, but never forward the API's Set-Cookie
  // on proxied data calls — only the OAuth callback route sets the session cookie.
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("set-cookie");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}
