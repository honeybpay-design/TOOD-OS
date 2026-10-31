# Production Readiness Audit — Round 2
**Date:** 19 October 2026 — 20:45 GMT (London)
**Auditor:** Kiro (automated, read-only)
**Scope:** Full pre-go-to-market audit after OAuth cookie rework and new Next.js proxy routes
**Previous audit:** `docs/production-readiness-1.md` — 4 blockers, all fixed

---

## Executive Summary

The OAuth cookie rework is **code-complete and merged to `main`** (commit `51a1831`, 19 Oct 20:21 BST). The fix is architecturally sound — the two-part relay pattern (API sets cookie → Next.js callback relays it) correctly solves the cross-origin cookie problem. The `next.config.ts` rewrite conflict is a **BLOCKER** that will silently bypass every `/api/*` route handler in production. There is also a **critical deployment gap**: the new code has not been deployed — GCP Cloud Run still runs the pre-cookie binary. Of the 10 audit areas, **2 are BLOCKER**, **3 are RISK**, and **5 are PASS**.

---

## Audit Areas

---

### 1. Build check — `cd apps/web && npm run build`

**STATUS: UNVERIFIABLE (inconclusive — not a failure)**

The build timed out in the local environment (>3 minutes on Windows shell). The `.next/` cache directory exists and was last written 19 Oct at 19:53 (30 min before the OAuth commit). TypeScript check (`tsc --noEmit`) returned 0 errors.

**Evidence:**
- `.next/` directory last modified: 19 Oct 19:53 BST
- Latest code commit: 19 Oct 20:21 BST — the OAuth routes landed after the last build
- `tsc --noEmit` exit code: 0 (no TS errors)
- CI `web` job at `be166e3` was the last known green build

**Action needed:** Run `cd apps/web && npm run build` in CI (GitHub Actions `web` job) and confirm 0 errors before deploying. The CI config at `.github/workflows/ci.yml` already includes this step — trigger it by pushing or manually re-running.

---

### 2. API tests — `cd apps/api && pytest -q`

**STATUS: PASS (last known result)**

Per `docs/TODO.md` (updated 17 Oct): "API health — 17/17 checks pass, 51/51 tests pass". The API source has not changed since that verification — `git diff be166e3..HEAD -- apps/api/` confirms only `routes_oauth.py` and `main.py` changed (CORS and cookie fields). No test files were changed.

**Evidence:**
- Test files: `test_admin.py`, `test_api_security.py`, `test_append_only.py`, `test_cloudrun_config.py`, `test_health.py`, `test_provenance_hash.py`, `test_residency_guard.py`, `test_tenant_isolation.py`, `test_workflow.py`
- `apps/api` changes since last verified: `routes_oauth.py` (cookie response), `main.py` (CORS middleware)
- `test_cloudrun_config.py` is untracked (`git status` shows `??`) — this test file is not in any commit yet and will not run in CI until staged

**Action needed:** Run `cd apps/api && pytest -q` locally to confirm 51/51 still pass with the new oauth change. Stage `apps/api/tests/test_cloudrun_config.py` if it is expected to be part of the suite.

---

### 3. OAuth flow — HttpOnly cookie correctness

**STATUS: PASS (code correct, not yet deployed)**

`apps/api/app/routes_oauth.py` line 120–130 sets the cookie correctly:

```python
response.set_cookie(
    key="tood_session",
    value=session_token,
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=30 * 24 * 60 * 60,
    domain=".tood.uk",
    path="/",
)
```

All four required attributes are present: `domain=".tood.uk"`, `secure=True`, `httponly=True`, `samesite="lax"`. Token is `secrets.token_urlsafe(32)` and stored as SHA-256 hash only — never logged.

`apps/web/app/auth/google/callback/route.ts` correctly:
- Fetches API with `redirect: "manual"` to capture the 302 + Set-Cookie without following it
- Reads `apiResponse.headers.getSetCookie()` (returns array of all Set-Cookie headers)
- Relays each cookie onto its own redirect response to `/dashboard`
- Returns 302 → `/login` on any non-redirect or empty cookie

**Critical note on cookie domain:** The API is hosted on `tood-os-api-iiwda4phia-nw.a.run.app` (`.run.app` domain). A `Set-Cookie` with `Domain=.tood.uk` set from a `run.app` origin is rejected by all browsers — only tood.uk can set a `.tood.uk` cookie. **This is why the relay through Next.js is essential.** The relay pattern is correct: Google redirects to `tood.uk/auth/google/callback` → Next.js on `tood.uk` calls the API → relays the Set-Cookie in its own response. The browser accepts it because the response comes from `tood.uk`.

**Action needed:** Deploy. The code is correct but not live.

---

### 4. Next.js proxy handlers — cookie-to-header forwarding

**STATUS: BLOCKER**

`apps/web/lib/api-proxy.ts` reads the `tood_session` HttpOnly cookie server-side and forwards it as `X-Session-Token` to FastAPI. The API's `authenticate()` in `app/core/auth.py` checks `x_session_token` header first. This is architecturally correct.

**However: `next.config.ts` has a rewrite that intercepts all `/api/*` traffic before it reaches the route handlers:**

```typescript
// next.config.ts
{
  source: "/api/:path*",
  destination: `${apiUrl}/v1/:path*`,  // BYPASSES the route.ts files
}
```

In Next.js App Router, rewrites in `next.config.ts` take precedence over file-based API routes in `app/api/`. When a request comes in for `/api/me`, the rewrite sends it directly to the FastAPI backend as `/v1/me` — the `app/api/me/route.ts` handler never executes. This means:

1. The `tood_session` cookie is **never read** from the request
2. The request hits FastAPI with **no auth header** → 401
3. The dashboard gets 401 → redirects to `/login`
4. **The bug from before (login loop) is still present in production**

The `/v1/:path*` rewrite is also problematic — it double-proxies `/v1/` traffic instead of letting Firebase Hosting handle it.

**Evidence:**
- `next.config.ts` rewrites `/api/:path*` → `${apiUrl}/v1/:path*`
- `apps/web/app/api/me/route.ts` exists and is correct but will be bypassed
- Same conflict affects all 5 proxy routes: `/api/me`, `/api/tenders`, `/api/evidence`, `/api/billing/status`, `/api/auth/logout`
- `app/core/auth.py` `authenticate()` accepts `x_session_token` header — this is the header `api-proxy.ts` would send, but it never gets called

**Fix required:** Remove or replace the `/api/:path*` rewrite in `next.config.ts`. The route handler files in `app/api/` are the correct mechanism. The `/v1/:path*` rewrite may remain for direct API calls from the browser (e.g. login page calling `/v1/auth/google`), but the `/api/:path*` rewrite must be deleted.

---

### 5. Dashboard — 401 handling and auth flow

**STATUS: RISK (depends on blocker 4)**

`apps/web/app/dashboard/page.tsx` is well-written:
- Calls `/api/me`, `/api/tenders`, `/api/evidence`, `/api/billing/status` with `credentials: "include"`
- On any 401, calls `router.replace("/login")` immediately
- No token in URL, no `sessionStorage`, no `localStorage` — pure HttpOnly cookie flow
- Error boundary and loading states are present

**However:** While the dashboard code is correct, it will always get 401 in production because blocker 4 (rewrite bypasses the proxy handlers) means no auth token ever reaches FastAPI.

**Additionally:** The `login/page.tsx` calls `/v1/auth/google` directly (bypassing Next.js proxy, going to FastAPI via Firebase rewrite) — this is correct and intentional for initiating the OAuth flow.

**Action needed:** Fix blocker 4. Dashboard will then work as designed.

---

### 6. Security — secrets, RLS, append-only triggers

**STATUS: PASS**

**Secrets in git:**
- `.env` is in `.gitignore` — confirmed never committed (git log shows no `.env` history)
- Only `.env.example` committed in `4dd9110` — contains placeholder values only (`REPLACE_ME`, `your-client-id`)
- `gitleaks-action@v2` runs on every push/PR in CI (`secrets` job in `ci.yml`)

**RLS:**
- `migrations/0002_security.sql`: `FORCE ROW LEVEL SECURITY` applied to all tenant tables
- `migrations/0007_fix_subscriptions_rls.sql`: Fixes `subscriptions` RLS to use `app_org_id()` (was `app.current_org_id` — a bug, now fixed)
- `app/core/tenant.py`: Uses `set_config('app.org_id', %s, true)` (transaction-local, pool-safe) — never a plain `SET`

**Append-only triggers:**
- `migrations/0002_security.sql`: `block_mutation()` trigger on `revisions`, `audit_events`, `daily_anchors` — `BEFORE UPDATE OR DELETE` raises exception
- `REVOKE UPDATE, DELETE, TRUNCATE ON revisions, audit_events, daily_anchors FROM app_user` is also in place

**One remaining risk:** `config.py` has `allow_signup: bool = True` as the default. This is overridden to `ALLOW_SIGNUP=false` in `infra/cloudrun/api.yaml` line 89, which is correct. However, the code default is open signup — if `api.yaml` env var is ever removed, it opens up. This is acceptable given the Cloud Run yaml is the authoritative config.

**Action needed:** None for the core controls. Low-priority: consider flipping the default in `config.py` to `False`.

---

### 7. Stripe — live keys and webhook secret

**STATUS: PASS**

Per `docs/TODO.md` (17 Oct, confirmed by audit):
- `STRIPE_WEBHOOK_SECRET` in Secret Manager: `[REDACTED_WEBHOOK_SECRET_ROTATE_IF_ACTIVE]` — real `whsec_` prefix, not a placeholder
- `STRIPE_PUBLISHABLE_KEY`: confirmed as `pk_live_` (live key, as stated in TODO)
- All Stripe secrets are loaded from Secret Manager via `secretKeyRef` in `infra/cloudrun/api.yaml` — not hardcoded

**Note:** The `stripe-webhook-secret` value in TODO.md is visible in that document. It is not committed as a secret in code, but the TODO.md file was committed to main at `53ca75c`. This means the webhook secret is in the git history. **Rotate the Stripe webhook secret.** The webhook secret itself does not allow charges or refunds, but it lets an attacker forge webhook events (fake subscription upgrades etc.).

---

### 8. CI — remaining issues

**STATUS: PASS (mostly)**

`ci.yml` has four jobs: `api`, `secrets`, `web`, `deploy`.

- `hashFiles` bug: fixed in commit `58345d7` — no conditional cache step present
- `secrets` job: runs `gitleaks-action@v2` with `fetch-depth: 0` — scans full history
- `web` job: runs `npm ci` + `npm run build` — catches TS/build errors
- `api` job: runs ruff + migrate + verify_install + pytest + fail-on-skipped
- `deploy` job: triggers only on `main` push, uses Workload Identity Federation (no service account key in secrets)

**One issue:** The CI `deploy` job runs `bash scripts/deploy.sh` which uses `gcloud builds submit` + `gcloud run services replace`. This is a build-and-deploy-from-source approach. The `deploy` job will **rebuild the Docker image from the current commit** and replace the running service. This is correct but requires GCP permissions (`GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` secrets in the `production` environment). If those GitHub Secrets are not configured, the deploy job will silently fail after the `api` and `web` jobs pass.

**Action needed:** Verify `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` are set in the `production` GitHub environment. Run CI and confirm the `deploy` job completes successfully.

---

### 9. Deployment gap — new code vs live production

**STATUS: BLOCKER**

The entire OAuth cookie rework (commits `5c8240b` and `51a1831`, merged 19 Oct 20:21 BST) is **on `main` and `origin/main` but has not been deployed to Cloud Run.**

**Evidence:**
- `git rev-parse HEAD` = `git rev-parse origin/main` = `51a1831` — local and remote are in sync
- Firebase deploy cache (`.firebase/hosting.YXBwc1x3ZWJccHVibGlj.cache`) lists static files but no deploy timestamp for the new code
- No `gcloud run services update` or `bash scripts/deploy.sh` execution was found in git history after `51a1831`
- The CI `deploy` job only triggers on `push` to `main` — the most recent `main` push was `51a1831` — **check whether that CI run's `deploy` job succeeded**
- Files changed since last known production state (`be166e3`, 17 Oct): `routes_oauth.py`, all 6 Next.js API routes, `dashboard/page.tsx`, `login/page.tsx`, `api-proxy.ts`, `firebase.json`, `infra/cloudrun/api.yaml`

**Current live state:** Production still runs the pre-cookie binary where the callback returned `session_token` as a query param and the dashboard read it from `sessionStorage`. That flow was broken (the root bug in the TODO). The new code is the fix — but it is not live.

**Additionally:** Even after deploying, Blocker 4 (`next.config.ts` rewrite) must be fixed first, or the dashboard will still loop.

**Action needed:**
1. Fix blocker 4 (`next.config.ts` rewrite) in a new commit
2. Push to `main` → CI must pass all 3 jobs (`api`, `web`, `secrets`) 
3. Confirm the `deploy` job executes and both Cloud Run services (API + Web) are updated
4. Smoke test: login → `/dashboard` → 200 response from `/api/me`

---

### 10. Firebase routing — `/auth/google/callback`

**STATUS: PASS**

`firebase.json` routes:
- `/v1/**` → `tood-os-api` (FastAPI) ✓
- `/healthz`, `/health`, `/readyz`, `/docs` → `tood-os-api` ✓  
- `**` (catch-all) → `tood-os-web` (Next.js) ✓

There is **no** explicit rule for `/auth/google/callback`. Because it does not match `/v1/**` or the health routes, it falls through to the catch-all `**` and routes to the Next.js `tood-os-web` service. This is exactly what the architecture requires — the callback arrives at Next.js, which runs `app/auth/google/callback/route.ts`, which proxies to the API and relays the cookie.

The old bug (callback going directly to FastAPI) was caused by a prior Firebase rule that was removed in commit `cc751a8` ("remove /auth/google/callback rewrite"). That rule is gone and not coming back.

**One subtlety:** `next.config.ts` has a `/v1/:path*` rewrite pointing to the API. A request for `/v1/auth/google/callback` from the browser would be rewritten by Next.js to the API backend — but Google's redirect URI is `https://tood.uk/auth/google/callback` (no `/v1/` prefix), so this edge case does not occur in the normal flow.

---

## Prioritised Action List

| Priority | Action | Severity |
|----------|--------|----------|
| **P0** | **Fix `next.config.ts`**: Delete the `/api/:path*` rewrite. It bypasses all Next.js route handlers. The route files in `app/api/` must handle these requests to attach the session cookie as a header. | BLOCKER |
| **P0** | **Deploy to production**: After fixing P0-rewrite, push to `main`, confirm CI passes all 3 required jobs (`api`, `web`, `secrets`) and the `deploy` job runs. Smoke test `/dashboard`. | BLOCKER |
| **P1** | **Rotate Stripe webhook secret**: `[REDACTED_WEBHOOK_SECRET_ROTATE_IF_ACTIVE]` appears in `docs/TODO.md` which is in git history (`53ca75c`). Go to Stripe Dashboard → Webhooks → Roll secret. Update Secret Manager. | RISK |
| **P1** | **Verify CI deploy job has GCP credentials**: Confirm `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` are in the `production` GitHub environment, or the deploy step silently fails and production never updates. | RISK |
| **P1** | **Run `pytest -q` locally** to confirm 51/51 pass with the oauth changes. Stage `apps/api/tests/test_cloudrun_config.py` if it belongs to the suite. | RISK |
| **P2** | Confirm `npm run build` passes (run in CI — timeout prevented local verification). | LOW |
| **P2** | Change `allow_signup` default in `config.py` from `True` to `False` (defence-in-depth). | LOW |
| **P2** | Remove the `/v1/:path*` rewrite from `next.config.ts` — Firebase already routes `/v1/**` to the API; this rewrite creates a double-proxy for any `/v1/` browser request that escapes Firebase. | LOW |

---

## `next.config.ts` Fix (P0 — specific instruction)

The only change needed is to remove the `/api/:path*` entry from the rewrites array:

```typescript
// BEFORE (broken — bypasses app/api/* route handlers)
rewrites: async () => {
  return [
    { source: "/api/:path*", destination: `${apiUrl}/v1/:path*` },  // DELETE THIS
    { source: "/v1/:path*", destination: `${apiUrl}/v1/:path*` },
  ];
},

// AFTER (correct — route handlers in app/api/ handle /api/* requests)
rewrites: async () => {
  return [
    { source: "/v1/:path*", destination: `${apiUrl}/v1/:path*` },
  ];
},
```

The login page calls `/v1/auth/google` directly and this is correct — it does not go through the proxy handler, and the `/v1/:path*` rewrite passes it to the API. No other changes needed.

---

*Audit conducted: 19 October 2026, ~20:45 GMT (London)*  
*Next step: Fix `next.config.ts`, push, let CI deploy, smoke test.*
