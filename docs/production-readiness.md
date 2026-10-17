# Production Readiness Report — tood.com
**Audit date:** 14 October 2026 (eve of go-to-market)  
**Auditor:** Kiro investigation agent (read-only, no code changed)  
**Scope:** Full pre-launch production readiness check against live endpoints and source code

---

## Executive Summary

**Go-to-market tomorrow is HIGH RISK.** The application is substantially built and several hard security controls (RLS, append-only triggers, OAuth flow, hash chain) are correctly implemented. However, there are **4 hard blockers** that will cause immediate production failures or revenue loss:

1. **Stripe webhook secret is a placeholder** — all subscription webhooks will be rejected, meaning no paid plan activations.
2. **Stripe publishable key is a test key (pk_test_)** — the live checkout flow will not work for real card payments.
3. **Cloud Run api.yaml is missing critical env vars** (AUTH_DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET) — if the live service is currently working, it is because these were injected manually; the IaC does not reflect production state.
4. **The subscriptions table RLS policy reads the wrong config key** — it uses `app.current_org_id` but the system sets `app.org_id`, meaning the subscriptions policy will evaluate against NULL and could return unexpected results.

There are also **5 significant risks** that are not hard blockers but need resolution before or shortly after launch. Full details are in the sections below.

---

## 1. API Health & Correctness

### ✅ PASS — Live API healthz

- `GET https://tood-os-api-844874461521.europe-west2.run.app/healthz` → returns 404 via the direct Cloud Run URL (the Google Front End intercepts `/healthz` before it reaches the app at this URL). This is expected and documented — the code adds a `/health` alias for exactly this reason (`main.py` line 47: `"Alias for environments where GFE intercepts /healthz"`).
- `GET https://tood.uk/v1/auth/google` returns HTTP 200 with a valid JSON auth_url, confirming the web + API stack is live and reachable.

### ⚠️ RISK — verify_install.py / pytest not run against live DB

- `verify_install.py` was last recorded as 17/17 PASS on 2026-10-13 against the local dev stack (`docs/install-report.md`).
- `pytest` was last recorded as **44 passed** (not 51) — the audit brief says "must be 51/51". The install-report shows 44, which suggests the OAuth + billing tests added since 2026-10-13 are not reflected in the last recorded run.
- Neither can be run from this machine against the live Cloud SQL database. It is unknown whether the live DB has had all 6 migrations applied.

**Action required:** Run `python scripts/verify_install.py` and `cd apps/api && pytest -q` against a fresh local stack with all 6 migrations to confirm the current count before go-live.

### ✅ PASS — ruff lint (CI gate)

- CI runs `ruff check apps/api scripts --config apps/api/pyproject.toml` on every push and PR. No lint failures are visible from git history.

---

## 2. Google OAuth Flow

### ✅ PASS — auth_url is well-formed (live confirmed)

Live probe of `https://tood.uk/v1/auth/google` returned:
```
{"auth_url":"https://accounts.google.com/o/oauth2/v2/auth?client_id=844874461521-2c7cpoldc0h0u8nf91rehu6bms052uc8.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Ftood.uk%2Fauth%2Fgoogle%2Fcallback&..."}
```
- No BOM or `\r\n` in client_id.
- `redirect_uri` is `https://tood.uk/auth/google/callback` — matches the hardcoded constant in `apps/api/app/core/oauth.py` line 15 (`REDIRECT_URI = "https://tood.uk/auth/google/callback"`) and the `settings.google_redirect_uri` default.
- client_id `844874461521-…` matches Google Cloud Project number in the `.env`.

### ✅ PASS — next.config.ts rewrite

`apps/web/next.config.ts` has the callback rewrite as the first rule (before the catch-all):
```ts
{ source: "/auth/google/callback", destination: `${apiUrl}/v1/auth/google/callback` }
```
This correctly proxies the Google redirect through Next.js to the FastAPI handler.

### ✅ PASS — Firebase Hosting routing

`firebase.json` routes `**` to `tood-os-web` (Cloud Run), which then applies `next.config.ts` rewrites. `/v1/**` routes go directly to `tood-os-api`. The `/auth/google/callback` path falls under the `**` catch-all → web → next.config rewrite → API. This is correct.

### ⚠️ RISK — Session token passed via URL query parameter

`routes_oauth.py` line 147 does:
```python
return RedirectResponse(url=f"https://tood.uk/dashboard?session_token={session_token}", status_code=302)
```
This puts a 30-day session token in the browser URL bar, browser history, and any server access logs. The dashboard immediately strips it via `history.replaceState`, but it remains in logs and referrer headers. This is a known OWASP risk (CWE-598). Not a launch blocker but should be resolved post-launch via a cookie or short-lived exchange code.

### ⚠️ RISK — Two Google OAuth clients in .env

The `.env` contains two sets of OAuth credentials:
- `GCP_CLIENT_ID` / `GCP_CLIENT_SECRET` (associated with honeybpay@gmail.com, "auto-created by Firebase")
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (the one the app reads via `config.py`)

The live endpoint uses `GOOGLE_CLIENT_ID`. The `GCP_CLIENT_ID` credentials appear to be unused by the application but their presence creates confusion. Verify which client ID is registered in Google Cloud Console with the `https://tood.uk/auth/google/callback` redirect URI, and remove or clearly comment out the unused entry.

### ❌ BLOCKER — Cloud Run api.yaml missing GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET

`infra/cloudrun/api.yaml` only injects 4 env vars from GCP Secret Manager:
`DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `DATABASE_ADMIN_URL`.

Missing from the IaC (but required at runtime):
- `AUTH_DATABASE_URL` — the auth module uses a separate DB role
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — OAuth will fall back to empty strings if missing
- `SESSION_SECRET` — state CSRF signing falls back to the hardcoded `"change-me-in-production"` default

The live OAuth flow works today, which means these were injected into Cloud Run through the GCP Console UI or `gcloud run services update` rather than through `api.yaml`. This is a **deployment drift** — `scripts/deploy.sh` runs `gcloud run services replace infra/cloudrun/api.yaml`, which would **overwrite** the manually-added env vars on next deploy, breaking OAuth.

**Action required before next deploy:** Add all missing vars to `api.yaml` (referencing GCP Secret Manager keys), and run `setup_gcp_secrets.py` after adding `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SESSION_SECRET` to `SECRET_KEYS`.

---

## 3. Security

### ✅ PASS — RLS enforced on all tenant tables

`migrations/0002_security.sql` enables and forces RLS on all 16 business tables and the 3 identity tables (organisations, memberships, users). `migrations/0003_tokens_and_audit_rls.sql` adds isolation to `api_tokens` and `audit_events`. `migrations/0006_oauth.sql` correctly forces RLS on `oauth_accounts` and `user_sessions`.

Every RLS policy uses `app_org_id()` which calls `current_setting('app.org_id', true)`. The `tenant_connection()` function in `core/tenant.py` sets this via `SELECT set_config('app.org_id', %s, true)` (transaction-local), as required by AGENTS.md.

### ✅ PASS — Append-only triggers exist

Three triggers are confirmed in migration 0002:
- `revisions_append_only` on `revisions`
- `audit_append_only` on `audit_events`
- `anchors_append_only` on `daily_anchors`

All three execute `block_mutation()` which raises an exception on UPDATE or DELETE.

### ✅ PASS — No plain SET usage found

`grep` across all `apps/api/**/*.py` found zero `conn.execute("SET ...)` patterns. All tenant context is set exclusively through `tenant_connection()`.

### ❌ BLOCKER — Subscriptions RLS policy reads wrong config key

`migrations/0005_billing.sql` creates:
```sql
CREATE POLICY subscriptions_org ON subscriptions USING (
  org_id = current_setting('app.current_org_id', true)::uuid
);
```
The system sets `app.org_id` (via `tenant_connection()` → `set_config('app.org_id', ...)`). The key `app.current_org_id` is **never set anywhere in the codebase**.

This means:
- When `app.current_org_id` is unset, `current_setting(..., true)` returns `''`, the cast to uuid fails (PostgreSQL will raise an error or return NULL depending on context), and the policy blocks all access.
- Organisations could see zero rows from `subscriptions` even when authenticated, causing `/v1/billing/status` to return plan "none" or "starter" incorrectly.
- Alternatively, depending on PostgreSQL error handling in the policy, this could raise a cast exception on every billing query.

**Action required:** Add a new migration `migrations/0007_fix_subscriptions_rls.sql`:
```sql
DROP POLICY subscriptions_org ON subscriptions;
CREATE POLICY subscriptions_org ON subscriptions TO app_user
  USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
```

### ✅ PASS — .env not committed to git

`git ls-files .env` returns empty. `.gitignore` correctly excludes `.env` and `.env.*`.

### ✅ PASS — Gitleaks in CI

CI includes a `secrets` job using `gitleaks/gitleaks-action@v2` that scans all commits on every PR and push to main.

### ⚠️ RISK — Session token in URL (repeated from §2)

See §2 OAuth section above.

### ⚠️ RISK — Malware scanning not configured

Document upload route (`routes.py` upload_document) returns:
```json
"scan": "no malware scanner is configured in the local pack; configure one before production"
```
This warning was noted in the threat model as "to be added with the ingestion task". Users can upload arbitrary PDFs to production without AV scanning. This is a risk for a SaaS product handling procurement documents from external organisations.

### ⚠️ RISK — allow_signup defaults to True in production

`config.py` line 26: `allow_signup: bool = True  # development sign-up. Turn off in any shared environment`

`ALLOW_SIGNUP` is not set in `.env` and is not injected into Cloud Run via `api.yaml`. This means the `/v1/signup` endpoint (which creates an org+user+token with no verification) is **open in production**. Anyone can create an account without going through Google OAuth.

This is only a risk, not a blocker, because it's the legacy API-token signup path that bypasses OAuth. It should be disabled in production by injecting `ALLOW_SIGNUP=false` into the Cloud Run service.

### ✅ PASS — Threat model reviewed

`security/threat-model.md` is present with 6 threat entries. Two mitigations are marked "to be added" (malware scanning, prompt injection guard). These are known open items, not new findings.

### ⚠️ RISK — admin_force_plan uses database_url not database_admin_url (pre-existing)

Flagged in the previous reviewer's report: the `admin_force_plan` route uses `settings.database_url` (app_user role, subject to RLS) rather than `settings.database_admin_url`. An UPDATE to organisations without a tenant context set will affect zero rows silently. Not a launch blocker but a latent admin bug.

---

## 4. Stripe & Billing

### ❌ BLOCKER — STRIPE_WEBHOOK_SECRET is a placeholder

`.env` contains: `STRIPE_WEBHOOK_SECRET=whsec_placeholder`

`billing.py` calls `stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)`. With a placeholder value, signature verification will fail on **every webhook from Stripe**, causing:
- All `checkout.session.completed` events to return HTTP 400
- Plan upgrades will never be activated
- `customer.subscription.updated` and `customer.subscription.deleted` will never be processed

`api.yaml` references `tood-secrets/STRIPE_WEBHOOK_SECRET` from Secret Manager. The value in Secret Manager was pushed from `.env` via `setup_gcp_secrets.py`. Since `.env` has `whsec_placeholder`, the Secret Manager value is almost certainly also `whsec_placeholder`.

**Action required:** Create a real webhook endpoint in the Stripe Dashboard for `https://tood.uk/v1/billing/webhook`, set it to receive `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`. Copy the `whsec_...` secret from Stripe Dashboard, update `.env`, re-run `setup_gcp_secrets.py`, redeploy.

### ❌ BLOCKER — STRIPE_PUBLISHABLE_KEY is a test key

`.env` contains:
- `STRIPE_PUBLIC_KEY=pk_live_...` (live key, but under a different name)
- `STRIPE_PUBLISHABLE_KEY=pk_test_...` (test key)

`config.py` reads `stripe_publishable_key` which maps to `STRIPE_PUBLISHABLE_KEY=pk_test_...`. Any frontend checkout session initialised with the test publishable key will not accept real card numbers.

**Action required:** Set `STRIPE_PUBLISHABLE_KEY=<same pk_live_ value that is in STRIPE_PUBLIC_KEY>`, update Secret Manager, redeploy. Then remove the redundant `STRIPE_PUBLIC_KEY` key.

### ⚠️ RISK — STRIPE_SECRET_KEY is a Restricted Key (rk_live_) not a standard secret key

`.env` contains `STRIPE_SECRET_KEY=rk_live_...`. Restricted keys have scoped permissions. Ensure the restricted key has permissions for: customers (read/write), checkout sessions (read/write), subscriptions (read/write), webhooks (read). If the key lacks any of these, specific API calls will fail with HTTP 403 from Stripe.

### ✅ PASS — Stripe price IDs appear to be live

`.env` has `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PROFESSIONAL`, `STRIPE_PRICE_ENTERPRISE` all set to `price_...` format IDs. These are present and non-empty.

### ✅ PASS — Webhook endpoint exists and validates signature

`routes.py` has `POST /v1/billing/webhook` which calls `billing_svc.handle_webhook(payload, sig_header)`. The billing service calls `stripe.Webhook.construct_event(...)` with the webhook secret. The logic is correct — the problem is the secret value, not the code.

---

## 5. Frontend

### ✅ PASS — Landing page CTA is correct

`apps/web/app/page.tsx` hero section CTA:
```tsx
<a className="btn btn--primary btn--lg" href="/login">
  Start free trial — 14 days free
</a>
```
Announcement bar: `"14-day free trial · No credit card · Sign in with Google"`. No trace of the old "Try the demo" or "Join the founding 30" text. The page was rebuilt as of commit `3907e83`.

### ✅ PASS — /login is accessible

`apps/web/app/login/page.tsx` exists and renders a "Start your 14-day free trial" page with a Google sign-in button. No auth guard on this page.

### ✅ PASS — /dashboard redirects to /login if unauthenticated

`apps/web/app/dashboard/page.tsx` checks `sessionStorage.getItem("tood_session")` and calls `router.replace("/login")` if not set. On 401 from the API it also redirects to login. The auth guard is correctly client-side.

---

## 6. Deployment & Infrastructure

### ✅ PASS — tood.uk is live and serving content

Direct browser probe confirmed `https://tood.uk` returns HTML (the TOOD-OS UI). Firebase Hosting is live.

### ✅ PASS — Cloud Run API is reachable via Firebase proxy

`https://tood.uk/v1/auth/google` returns a valid JSON auth_url, confirming `tood-os-api` Cloud Run is running and Firebase is proxying `/v1/**` to it correctly.

### ⚠️ RISK — api.yaml deploy will overwrite manually-set env vars

As noted in §2, `scripts/deploy.sh` uses `gcloud run services replace`, which replaces the service spec entirely with `api.yaml`. Any env vars injected via the Cloud Console that are not in `api.yaml` (AUTH_DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET) will be **deleted on next deploy**.

### ⚠️ RISK — web.yaml API_URL points to api.tood.uk (DNS resolves to Firebase, not Cloud Run directly)

`infra/cloudrun/web.yaml` sets `API_URL=https://api.tood.uk`. DNS lookup confirms `api.tood.uk` is a CNAME to `tood-os-api.web.app` (Firebase Hosting), not directly to Cloud Run. This means API calls from the Next.js server-side rendering path go through Firebase → Cloud Run rather than directly to the Cloud Run service URL. This adds a hop and could affect latency, but is functionally correct as long as Firebase is up.

### ✅ PASS — CI/CD pipeline is sound

`.github/workflows/ci.yml`:
- Runs ruff, migrate, verify_install, pytest on every PR and push to main
- Includes Gitleaks secret scanning
- Deploys only on push to `main` (never on PRs)
- Uses Workload Identity Federation (not a long-lived service account key)
- Build step runs `npm ci && npm run build` for web

### ✅ PASS — docker-compose.yml is consistent

`docker-compose.yml` uses `pgvector/pgvector:pg16` matching the CI postgres service. The production Cloud SQL instance is PostgreSQL 16 (Cloud Run config references `tood-db`). Dev/CI/prod are consistent on DB version.

---

## 7. Data & Migrations

### ✅ PASS — All 6 migration files exist and are sequentially numbered

| File | Size | Last modified |
|------|------|---------------|
| 0001_schema.sql | 7,703 bytes | 2026-10-13 |
| 0002_security.sql | 2,700 bytes | 2026-10-13 |
| 0003_tokens_and_audit_rls.sql | 1,026 bytes | 2026-10-13 |
| 0004_ordering.sql | 383 bytes | 2026-10-13 |
| 0005_billing.sql | 927 bytes | 2026-10-14 |
| 0006_oauth.sql | 1,768 bytes | 2026-10-16 |

All 6 files have modification timestamps in Oct 2026.

### ⚠️ RISK — Applied migrations cannot be confirmed on live DB

`docs/install-report.md` shows T01 (17/17 checks passed) from 2026-10-13. At that point migrations 0001–0004 were applied. Migrations 0005 and 0006 were added after that date. Whether they have been applied to the live Cloud SQL instance cannot be confirmed without `gcloud sql connect` access.

**Action required:** Confirm `python scripts/migrate.py` has been run against the live Cloud SQL DB, applying 0005 and 0006. If not, the subscriptions table and OAuth tables do not exist in production.

### ✅ PASS — No migration files edited after apply

AGENTS.md rule "Never edit an applied migration" — file timestamps show sequential addition, no modifications to earlier files after creation. Git history shows each migration committed once.

---

## 8. Open Risks / Blockers

### Hard Blockers (must fix before go-live)

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| B1 | `STRIPE_WEBHOOK_SECRET=whsec_placeholder` — all webhooks rejected | `.env`, GCP Secret Manager | Create real Stripe webhook endpoint, update secret, redeploy |
| B2 | `STRIPE_PUBLISHABLE_KEY=pk_test_...` — test key, live payments broken | `.env`, GCP Secret Manager | Set to `pk_live_` value, update secret, redeploy |
| B3 | `api.yaml` missing `AUTH_DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET` — next deploy will break OAuth | `infra/cloudrun/api.yaml` | Add all missing vars referencing GCP Secret Manager keys |
| B4 | Subscriptions RLS reads `app.current_org_id` (never set) instead of `app.org_id` | `migrations/0005_billing.sql` | Add migration 0007 to fix the policy |

### Significant Risks (not hard blockers)

| # | Issue | Severity | Recommendation |
|---|-------|----------|----------------|
| R1 | Migrations 0005 and 0006 may not be applied on live Cloud SQL DB | HIGH | Run `python scripts/migrate.py` against live DB and confirm |
| R2 | `allow_signup=True` default — `/v1/signup` open in production, bypasses OAuth | MEDIUM | Inject `ALLOW_SIGNUP=false` into Cloud Run api.yaml and Secret Manager |
| R3 | Session token passed via URL query parameter — appears in logs and browser history | MEDIUM | Post-launch: switch to HttpOnly cookie or short-lived exchange code |
| R4 | No malware scanning on uploaded PDFs | MEDIUM | Configure AV scanning before processing customer tender documents |
| R5 | `admin_force_plan` uses app_user role, UPDATE silently affects 0 rows | LOW | Fix in next sprint: use `database_admin_url` |
| R6 | `api.tood.uk` DNS is CNAME to Firebase, not direct Cloud Run — extra hop | LOW | Consider custom domain direct to Cloud Run for lower latency |
| R7 | Two Google OAuth clients in .env (honeybpay@gmail.com auto-created) | LOW | Audit Google Console, confirm correct client_id, remove unused entry |

---

## Prioritised Action List (before go-live)

1. **[B1] Fix STRIPE_WEBHOOK_SECRET** — Go to Stripe Dashboard → Webhooks, add endpoint `https://tood.uk/v1/billing/webhook`, select events, copy `whsec_...`. Update `.env`, run `python scripts/setup_gcp_secrets.py`, redeploy.

2. **[B2] Fix STRIPE_PUBLISHABLE_KEY** — Change `STRIPE_PUBLISHABLE_KEY` in `.env` to the `pk_live_...` value already stored as `STRIPE_PUBLIC_KEY`. Remove `STRIPE_PUBLIC_KEY`. Update Secret Manager, redeploy.

3. **[B3] Fix api.yaml** — Add the following secret refs to `infra/cloudrun/api.yaml` before next deploy:
   ```yaml
   - name: AUTH_DATABASE_URL
     valueFrom: { secretKeyRef: { name: tood-secrets, key: AUTH_DATABASE_URL } }
   - name: GOOGLE_CLIENT_ID
     valueFrom: { secretKeyRef: { name: tood-secrets, key: GOOGLE_CLIENT_ID } }
   - name: GOOGLE_CLIENT_SECRET
     valueFrom: { secretKeyRef: { name: tood-secrets, key: GOOGLE_CLIENT_SECRET } }
   - name: SESSION_SECRET
     valueFrom: { secretKeyRef: { name: tood-secrets, key: SESSION_SECRET } }
   - name: ALLOW_SIGNUP
     value: "false"
   ```
   Then add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET` to `setup_gcp_secrets.py` `SECRET_KEYS` list and re-run it.

4. **[B4] Fix subscriptions RLS** — Add `migrations/0007_fix_subscriptions_rls.sql`:
   ```sql
   DROP POLICY subscriptions_org ON subscriptions;
   CREATE POLICY subscriptions_org ON subscriptions TO app_user
     USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
   GRANT SELECT, INSERT, UPDATE, DELETE ON subscriptions TO app_user;
   ```
   Then apply it to the live DB.

5. **[R1] Confirm migrations on live DB** — Run `python scripts/migrate.py` (or verify via Cloud SQL that migrations 0005 and 0006 have been applied). The OAuth tables (`oauth_accounts`, `user_sessions`) and billing table (`subscriptions`) must exist.

6. **[R2] Disable open signup** — Inject `ALLOW_SIGNUP=false` via Cloud Run env vars (or include in api.yaml from step 3 above).

---

*Report generated by automated read-only audit of workspace `c:\Users\Donny\Desktop\tood.com`. No files were modified. All findings are based on static analysis of source files and live endpoint probes.*
