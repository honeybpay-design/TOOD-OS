import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Google OAuth callback.
 *
 * Google redirects here with code+state. We proxy to FastAPI which validates
 * and returns JSON { session_token: "..." }. We then set the cookie via a raw
 * Set-Cookie header on a 302 redirect response — this is the most reliable
 * way to set cookies in Next.js Route Handlers on Cloud Run behind Firebase.
 */
export async function GET(request: NextRequest) {
  const API_URL = process.env.API_URL;
  if (!API_URL) {
    console.error("[callback] API_URL env var is missing");
    return redirect("/login");
  }

  const search = request.nextUrl.search;
  const backendUrl = `${API_URL}/v1/auth/google/callback${search}`;

  let apiResponse: Response;
  try {
    // API now returns JSON { session_token } instead of 302+cookie
    apiResponse = await fetch(backendUrl, { redirect: "follow" });
  } catch (err) {
    console.error("[callback] fetch to API failed:", err);
    return redirect("/login");
  }

  console.log("[callback] API status:", apiResponse.status);

  if (!apiResponse.ok) {
    console.error("[callback] API returned error:", apiResponse.status);
    return redirect("/login");
  }

  let data: { session_token?: string };
  try {
    data = await apiResponse.json();
  } catch {
    console.error("[callback] failed to parse API JSON");
    return redirect("/login");
  }

  const sessionToken = data.session_token;
  console.log("[callback] sessionToken received:", !!sessionToken);

  if (!sessionToken) {
    console.error("[callback] no session_token in API response");
    return redirect("/login");
  }

  // Build the dashboard URL using the public-facing host
  const host =
    request.headers.get("x-forwarded-host") ??
    request.headers.get("host") ??
    "tood.uk";
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const dashboardUrl = `${proto}://${host}/dashboard`;

  // Set cookie via raw Set-Cookie header — most reliable method across
  // Next.js versions, Cloud Run, and Firebase Hosting proxy layers.
  const maxAge = 30 * 24 * 60 * 60;
  const cookieValue = `__session=${sessionToken}; Path=/; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Lax`;

  console.log("[callback] setting cookie and redirecting to dashboard");

  return new Response(null, {
    status: 302,
    headers: {
      "Location": dashboardUrl,
      "Set-Cookie": cookieValue,
    },
  });
}

function redirect(path: string): Response {
  return new Response(null, { status: 302, headers: { location: path } });
}
