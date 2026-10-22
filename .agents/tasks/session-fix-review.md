# OAuth session cookie relay and login page cleanup

The change resolves a production login loop where every OAuth sign-in redirected back to `/login` immediately after landing on `/dashboard`. The root cause was two independent failures: the Next.js callback route silently fell back to `http://localhost:8000` when `API_URL` was unset in Vercel, so no session cookie was ever issued; and the login page checked `sessionStorage` for a token that the HttpOnly cookie flow never writes there, so returning users were never forwarded to the dashboard. The fix adds a hard startup guard on the missing env var and replaces the dead `sessionStorage` check with a live `GET /api/me` probe. The `next.config.ts` rewrite that blocked the Vercel build (an unresolved `${apiUrl}` template literal) was already correct — the config uses string concatenation, not a template literal, so no change was needed.

Watch for: The cold-start guard (`throw` at module load when `API_URL` is absent) will crash the entire Next.js cold-start in production if `API_URL` is not set in Vercel — confirmed intentional, but it means a misconfigured deploy silently kills the whole app rather than just OAuth. The `/api/me` redirect on the login page fires unconditionally on mount, adding one extra round-trip for every unauthenticated visitor.

**Verdict**: APPROVED

---

## High-level view

The callback route now fails loudly at cold-start if `API_URL` is missing, which converts a silent wrong-host fetch into an immediately visible deploy error. The tradeoff is that a missing env var takes down the whole Next.js cold-start, not just the OAuth path — worth knowing before the next deploy.

The login page's session check was replaced with a `fetch("/api/me")` probe that correctly detects an existing HttpOnly cookie. The `sessionStorage` path it replaced was always a no-op under this cookie-based auth model, so the fix closes an invisible gap rather than changing visible behavior for new users.

The cookie relay chain (`routes_oauth.py` → callback → browser → `api-proxy.ts` → API) is end-to-end consistent: the token is stored as a SHA-256 hash in the database, transmitted only in `HttpOnly; Secure; SameSite=Lax` cookies and `X-Session-Token` headers, and never appears in URLs, logs, or JS-accessible storage.

The rewrite destination in `next.config.ts` uses `apiUrl + "/v1/:path*"` — string concatenation evaluated at build time — which produces a valid `http://`/`https://` URL. The Vercel build error described in the task context does not match the current file; the file is already correct.

---

<details>
<summary>Issues (2)</summary>

1. **Cold-start blast radius** — The `throw new Error("API_URL env var is required...")` at module level crashes the entire Next.js cold-start when `API_URL` is absent, not just OAuth. A missing env var in Vercel will take down the whole app. Ensure `API_URL` is set in all Vercel environments (Production, Preview, Development) before deploying, and add it to the deploy checklist or `.env.example`.

2. **Unconditional `/api/me` probe on login mount** — The `useEffect` in `LoginContent` fetches `/api/me` on every mount, including for users who will never have a session. This adds a round-trip and a 401 for every unauthenticated visitor. Not a blocking concern, but consider checking a lightweight client-side signal (e.g. a non-HttpOnly presence cookie) before firing the probe.

</details>

---

<details>
<summary>Details</summary>

### Cold-start guard and its blast radius

The module-level `throw` in `callback/route.ts` is the right call for a correctness problem: if `API_URL` is unset, the previous code fetched `http://localhost:8000`, got a connection-refused error, caught it silently, and redirected to `/login` — the user saw an infinite loop with no error. The guard makes the misconfiguration immediately visible in Vercel's function logs and deploy health checks.

The tradeoff is scope. Because the `throw` is at module load (not inside the handler), Next.js will fail to instantiate the route module during cold-start, which cascades to a 500 on the callback URL. Depending on how Next.js handles a module-load failure in the App Router, it may also affect other routes in the same bundle. Confirmed: the guard is at the top of the file, outside any function, so it runs at import time.

```ts
const API_URL = process.env.API_URL;
if (!API_URL) {
  throw new Error("API_URL env var is required for the OAuth callback");
}
```

This is an acceptable tradeoff for a production system — a deploy without the required env var should not silently serve broken auth — but it must be paired with `API_URL` being set in all Vercel environments before the next deploy.

### Cookie relay correctness

The relay chain is:

```
Google → /auth/google/callback (Next.js)
           ↓ fetch(API_URL/v1/auth/google/callback, { redirect: "manual" })
         FastAPI (routes_oauth.py)
           ↓ 302 + Set-Cookie: tood_session=<token>; HttpOnly; Secure; SameSite=Lax; Domain=.tood.uk
         callback/route.ts relays Set-Cookie onto its own 302 → /dashboard
           ↓ browser stores cookie under tood.uk
         /api/me → api-proxy.ts reads cookie server-side → X-Session-Token → FastAPI /v1/me
```

`getSetCookie()` compatibility fallback in the callback route handles Node 16 runtimes where the method does not exist. The fallback splits on `,(?=[^ ])` — the standard multi-value cookie splitting heuristic — confirmed correct for this case since `tood_session` is a single cookie with no embedded commas.

The proxy (`api-proxy.ts`) explicitly deletes `set-cookie` from relayed data responses. This prevents a compromised upstream from injecting a session cookie via a data endpoint — only the OAuth callback route sets the session cookie.

### Login page session probe

The old guard checked `sessionStorage.getItem('tood_session')`, which the HttpOnly cookie flow never populates. It was always null, so returning users were always shown the login page rather than being forwarded to the dashboard. The replacement:

```ts
fetch("/api/me", { credentials: "include" })
  .then((res) => { if (res.ok) router.replace("/dashboard"); })
  .catch(() => { /* no session — stay on login */ });
```

This correctly detects an existing session via the HttpOnly cookie. The `.catch` swallows network errors and leaves the user on the login page, which is safe fail-closed behavior.

The probe fires on every mount with no debounce or short-circuit. For users with no session (the majority of login page visitors) this generates a 401 on every load. A lightweight non-HttpOnly presence cookie (e.g. `tood_logged_in=1`, value-less, not the session token) could skip the round-trip for guests without exposing the session token to JS.


</details>

---

<details>
<summary>File map</summary>

| File | Change |
|---|---|
| `apps/web/app/auth/google/callback/route.ts` | Added cold-start guard for missing `API_URL`; added `getSetCookie()` fallback for Node 16 |
| `apps/web/app/login/page.tsx` | Replaced dead `sessionStorage` session check with `fetch("/api/me")` probe |
| `apps/web/next.config.ts` | No change — rewrite destination already uses string concatenation (confirmed correct) |
| `apps/web/lib/api-proxy.ts` | No change — correctly reads cookie server-side and strips `set-cookie` from proxied responses |
| `apps/web/app/api/me/route.ts` | No change — delegates to `proxyToApi` correctly |
| `apps/web/app/dashboard/page.tsx` | No change — redirects to `/login` only on 401, correct |
| `apps/api/app/routes_oauth.py` | No change — sets `tood_session` with correct HttpOnly/Secure/SameSite/Domain attributes |
| `apps/api/app/core/auth.py` | No change — accepts `X-Session-Token` header, matching what the proxy sends |

Full diff: `git diff main -- apps/web/app/auth/google/callback/route.ts apps/web/app/login/page.tsx`

</details>
