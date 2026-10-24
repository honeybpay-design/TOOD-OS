import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export const dynamic = "force-dynamic";

/**
 * Log the user out: invalidate the session server-side (the OAuth logout
 * endpoint reads the Authorization: Bearer header, routes_oauth.py), then clear
 * the HttpOnly `tood_session` cookie on the browser.
 *
 * The clearing Set-Cookie repeats the cookie's Domain/Path so the browser
 * actually removes the domain cookie rather than ignoring the expiry.
 */
export async function POST() {
  const cookieStore = await cookies();
  const token = cookieStore.get("__session")?.value;

  if (token) {
    try {
      await fetch(`${API_URL}/v1/auth/logout`, {
        method: "POST",
        headers: { authorization: `Bearer ${token}` },
      });
    } catch {
      // Swallow upstream errors — the cookie is cleared client-side regardless.
    }
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: {
      "content-type": "application/json",
      "set-cookie":
        "__session=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax",
    },
  });
}
