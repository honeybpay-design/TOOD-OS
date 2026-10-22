# Implementation Plan: Testimonial Removal + Session Fix

> Blueprint reference: Section 19 (OAuth / session), Section 25 (local/staging only).
> Files changed: `apps/web/app/login/page.tsx`, `apps/web/app/auth/google/callback/route.ts`,
> `apps/api/app/routes_oauth.py`.

---

## TASK 1 — Remove fake testimonial from login page

### What to remove

`apps/web/app/login/page.tsx` already has the testimonial gone — the right-hand panel currently
contains only the "What you'll get with your trial" benefits list. There is **no Sarah Chen block,
no 'Bid Director, NHS Trust' text, and no '60% bid preparation time' quote** in the file at the
time this plan was written.

**Action: none required for Task 1.** The testimonial has already been removed in a previous edit.
The implementer should confirm this by reading the file and checking that neither "Sarah Chen" nor
"Bid Director" nor "60%" appears in the JSX before marking this task done.

Files to verify: `apps/web/app/login/page.tsx`
Verify: `cd apps/web && npx tsc --noEmit` — compiles without errors, confirming the file is valid.

---

## TASK 2 — Fix dashboard session so user stays logged in after Google OAuth

### Root-cause analysis (traced end-to-end)

**The full intended flow:**

```
Browser → GET /v1/auth/google (Next.js rewrite → FastAPI)
         → window.location = auth_url (Google)
         → Google → browser → GET /auth/google/callback?code=…&state=…  (Next.js)
         → Next.js callback/route.ts → fetch(API_URL/v1/auth/google/callback, {redirect:"manual"})
         → FastAPI issues 302 + Set-Cookie: tood_session=…; Domain=.tood.uk
         → callback/route.ts relays Set-Cookie, redirects to /dashboard
         → browser stores tood_session cookie on .tood.uk
         → /dashboard loads, calls /api/me
         → /api/me/route.ts → proxyToApi → reads cookie server-side → x-session-token header
         → FastAPI /v1/me → authenticate() → Ctx
```

**Bug 1 (critical) — callback route does NOT set API_URL at build time in production:**

`apps/web/app/auth/google/callback/route.ts` uses:
```ts
const API_URL = process.env.API_URL ?? "http://localhost:8000";
```
In the Vercel/Cloud Run build environment `API_URL` is `${apiUrl}` (the literal string from the
old `next.config.ts` template) or simply absent.  **If `API_URL` is not injected as a real runtime
env var, the callback fetches `http://localhost:8000/v1/auth/google/callback` — a host that does
not exist in production — the fetch throws, the catch block redirects to `/login`.**

The same constant is declared in three places (`callback/route.ts`, `lib/api-proxy.ts`,
`app/api/auth/logout/route.ts`). They all rely on the same env var, so fixing the env var fixes
all three.

**Bug 2 (critical) — FastAPI sets the cookie with `domain=".tood.uk"` and the callback relays it
verbatim. This is correct. But the FastAPI callback also hard-codes the redirect destination to
`https://tood.uk/dashboard` (absolute URL).**

`routes_oauth.py` line:
```python
response = RedirectResponse(url="https://tood.uk/dashboard", status_code=302)
```

The Next.js callback ignores that destination and overwrites it:
```ts
headers.set("location", "/dashboard");
```
So the Next.js relative redirect to `/dashboard` is fine on tood.uk. No bug here, but it means the
FastAPI redirect target is irrelevant and the cookie relay is the only thing that matters.

**Bug 3 (critical) — `authenticate()` in `app/core/auth.py` does NOT read the cookie from the
request. It reads only:**
- `X-Session-Token` header
- `Authorization: Bearer` header

`proxyToApi` in `lib/api-proxy.ts` correctly reads the `tood_session` HttpOnly cookie server-side
and forwards it as `x-session-token`. That part is fine **as long as the cookie actually arrives
in the Next.js server-side cookie store** — which it will only do if Bug 1 is fixed (the cookie
must be set in the browser first).

**Bug 4 (login page) — `login/page.tsx` checks `sessionStorage.getItem('tood_session')` to skip
login:**
```ts
const token = sessionStorage.getItem('tood_session');
if (token) router.replace('/dashboard');
```
The real session is an HttpOnly cookie, not a sessionStorage entry. This check will never be true
after OAuth — it's a stale guard that used to work with a different token storage strategy. It
should be replaced with a lightweight `GET /api/me` check (or simply removed, since the dashboard
itself redirects to `/login` on 401). Leaving it in place means returning users who clear
sessionStorage will never get auto-forwarded to dashboard from the login page. Low severity but
confusing.

**Bug 5 (next.config.ts) — the Vercel build error reported by the user:**

```ts
// OLD (breaks Vercel):
const apiUrl = process.env.API_URL ?? "http://localhost:8000";
return [{ source: "/v1/:path*", destination: apiUrl + "/v1/:path*" }];
```

Vercel validates rewrite destinations at build time. If `API_URL` is not set in the build
environment, `apiUrl` is `"http://localhost:8000"` — which is a valid literal and the build
passes locally. But if `API_URL` is set to a value that evaluates to empty string or a non-http
scheme at Vercel build time, the destination fails validation. The current `next.config.ts` in the
repo already uses string concatenation (`apiUrl + "/v1/:path*"`) which is correct. Verify the
Vercel project has `API_URL` set to the full Cloud Run URL (e.g. `https://api-xyz-uc.a.run.app`).

---

### Implementation steps

#### Step 1 — Fix: `API_URL` must be available as a real runtime environment variable

This is the root cause of the 302 callback fetch failing in production.

**Files:** `apps/web/app/auth/google/callback/route.ts` (no code change needed — the variable read
is already correct). The fix is operational: `API_URL` must be set in the Vercel/Cloud Run
deployment configuration.

However, to make the callback code fail loudly and visibly instead of silently redirecting to
`/login` when `API_URL` is misconfigured, add an explicit guard at startup:

```ts
// At the top of callback/route.ts, after the import:
const API_URL = process.env.API_URL;
if (!API_URL) {
  throw new Error("API_URL env var is required for the OAuth callback");
}
```

This makes a misconfigured deploy crash at cold-start rather than silently breaking auth.

**Files to modify:** `apps/web/app/auth/google/callback/route.ts`

Do the same in `apps/web/lib/api-proxy.ts` (the proxy falls back to localhost silently today):

```ts
const API_URL = process.env.API_URL ?? "http://localhost:8000"; // keep fallback here for local dev
```
Keep the fallback in `api-proxy.ts` for local development — it is fine; the callback is the one
that must not silently fall back because it performs a server-to-server call to a host that only
exists in production.

**Files to modify:** `apps/web/app/auth/google/callback/route.ts`
**Verify:** `cd apps/web && npx tsc --noEmit` — no type errors. Then deploy and check that a
missing `API_URL` throws at startup with the explicit message.

---

#### Step 2 — Fix: relay Set-Cookie headers correctly including SameSite attribute

The callback in `route.ts` uses `apiResponse.headers.getSetCookie()` (available in Node 18+).
Verify this is available; if not, fall back to `apiResponse.headers.get("set-cookie")`.

Current code is correct on Node 18+. No change needed here — but add a defensive fallback so it
works on Node 16 environments:

```ts
// Replace the getSetCookie call:
const setCookies: string[] =
  typeof apiResponse.headers.getSetCookie === "function"
    ? apiResponse.headers.getSetCookie()
    : (apiResponse.headers.get("set-cookie") ?? "").split(/,(?=[^ ])/).filter(Boolean);
```

**Files to modify:** `apps/web/app/auth/google/callback/route.ts`

---

#### Step 3 — Fix: FastAPI `authenticate()` must also accept cookie-based sessions

This is a defence-in-depth fix. Currently `proxyToApi` reads the cookie server-side and forwards
it as `X-Session-Token`, so the cookie-to-header translation happens in Next.js. That works as
long as the cookie is present. No change is strictly required in `auth.py` for the primary flow to
work.

**No code change required in `auth.py` at this time.** The proxy pattern is correct and complete.

---

#### Step 4 — Fix: replace stale `sessionStorage` guard in login page

The login page's `useEffect` checks `sessionStorage.getItem('tood_session')` — but the session is
stored as an HttpOnly cookie, never in sessionStorage. This check always returns null and the
auto-redirect to `/dashboard` never fires for returning users.

Replace it with a lightweight `/api/me` check: if the server returns 200 the user is already
logged in and should be forwarded to `/dashboard`; if it returns 401 stay on the login page.

```ts
// Replace the useEffect in LoginContent:
useEffect(() => {
  fetch("/api/me", { credentials: "include" })
    .then((res) => { if (res.ok) router.replace("/dashboard"); })
    .catch(() => { /* stay on login */ });
}, [router]);
```

**Files to modify:** `apps/web/app/login/page.tsx`
**Verify:** `cd apps/web && npx tsc --noEmit` — no type errors.

---

#### Step 5 — Verify `next.config.ts` rewrite builds without error

The current `next.config.ts` already uses string concatenation for the rewrite destination. Ensure
the Vercel project has `API_URL` set to the full HTTPS Cloud Run URL before triggering a new build.
The config itself does not need a code change.

**Files to confirm (read-only):** `apps/web/next.config.ts`
**Verify:** `cd apps/web && npm run build` locally with `API_URL=https://your-api.run.app` set —
build must succeed with no "Invalid rewrite" error.

---

### Summary of concrete file changes

| File | Change |
|---|---|
| `apps/web/app/auth/google/callback/route.ts` | Throw if `API_URL` is missing; add `getSetCookie` fallback for Node 16 |
| `apps/web/app/login/page.tsx` | Replace `sessionStorage` guard with `/api/me` check |
| `apps/web/next.config.ts` | No code change needed; verify `API_URL` env var is set in Vercel |
| `apps/api/app/routes_oauth.py` | No code change needed; cookie attributes are correct |
| `apps/web/lib/api-proxy.ts` | No code change needed; proxy forwarding is correct |
| `apps/web/app/api/me/route.ts` | No code change needed |

### Deployment requirement (not a code change)

Set `API_URL=https://<cloud-run-host>` in the Vercel project environment variables (Settings →
Environment Variables → Production). Without this, every OAuth callback fetch goes to
`http://localhost:8000` and fails silently.

---

### Why the dashboard bounces to `/login`

The chain of failure in production:

1. `API_URL` is not set (or is a placeholder) in the Vercel build/runtime environment.
2. `callback/route.ts` fetches `http://localhost:8000/v1/auth/google/callback` — connection
   refused.
3. The `catch` block returns `redirectTo("/login")`.
4. No `Set-Cookie` is ever sent to the browser.
5. `tood_session` cookie is never stored.
6. Dashboard loads, calls `/api/me`, proxy finds no cookie, returns 401.
7. Dashboard `if (responses.some(r => r.status === 401)) router.replace("/login")` fires.
8. User sees the login page again.

Fixing `API_URL` in Vercel resolves the entire bounce loop.
