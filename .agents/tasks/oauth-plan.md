# Implementation Plan — Google OAuth & Cloud SQL Setup

Blueprint reference: section 19 (SSO/authentication), section 25 (staging-only credentials),
AGENTS.md hard rules (never weaken RLS, always use `tenant_connection()`, no plain SET,
never log secrets, append-only triggers untouched).

---

## Codebase facts discovered during exploration

- `apps/api/app/core/config.py` — `Settings` uses `pydantic-settings`; add new fields here.
- `apps/api/app/core/auth.py` — token-based auth today; OAuth adds alongside it without replacing it.
- `apps/api/app/core/tenant.py` — `tenant_connection()` uses `set_config(..., true)` (transaction-local); must be used for all customer queries.
- `apps/api/app/main.py` — `app.include_router(router)` / `app.include_router(admin_router)`. OAuth router registered here.
- `apps/api/app/routes.py` — `router = APIRouter(prefix="/v1")`. OAuth routes go in a separate `APIRouter` at `/v1/auth`.
- `migrations/` — five files (0001–0005); next is `0006_oauth.sql`.
- `scripts/migrate.py` — reads `DATABASE_ADMIN_URL`, calls `ensure_roles`, runs every `.sql` in `migrations/` in name order; idempotent.
- `apps/web/next.config.ts` — rewrites `/api/:path*` → `$API_URL/v1/:path*`; OAuth callback at `/auth/google/callback` needs a separate rewrite.
- `apps/web/app/` — `page.tsx` (landing), `dashboard/page.tsx` (placeholder), `layout.tsx`; no auth context yet.
- `pyproject.toml` — `google-auth>=2.30` already present; `itsdangerous` and `httpx` need adding.
- `.env` — `GCP_CLIENT_ID` and `GCP_CLIENT_SECRET` already present (from user's Google Cloud console); placeholder variables for `GOOGLE_REDIRECT_URI` and `SESSION_SECRET` must be added.

**Security hard rules embedded in every item below:**
- `GOOGLE_REDIRECT_URI` must equal `https://tood.uk/auth/google/callback` exactly.
- Never log `GOOGLE_CLIENT_SECRET`, `access_token`, or `session_token` (not even at DEBUG level).
- `STATE` parameter must be a signed value via `itsdangerous.URLSafeTimedSerializer`.
- Session token must be `secrets.token_urlsafe(32)` stored server-side in `user_sessions` table.
- All customer DB queries use `tenant_connection()`; `auth_user` role used for identity writes.
- RLS, append-only triggers, hash chain, export gate must not be touched.

---

## Phase 1 — Reset Cloud SQL postgres password and verify connectivity

- [ ] 1. Reset the Cloud SQL `postgres` superuser password via `gcloud` CLI so that
         `DATABASE_ADMIN_URL` can connect.
         **Decision:** Use `gcloud sql users set-password` (non-destructive, no data loss).
         Files: `.env` (update `DATABASE_ADMIN_URL` password after reset — do not commit).
         Verify:
         ```
         python - <<'EOF'
         import psycopg, os
         from scripts.migrate import load_env
         load_env()
         conn = psycopg.connect(os.environ["DATABASE_ADMIN_URL"], connect_timeout=5)
         print(conn.execute("SELECT version()").fetchone())
         conn.close()
         EOF
         ```
         Expected: PostgreSQL version string printed without error.
         Stop and report if this fails; do not proceed to Phase 2.

---

## Phase 2 — Create tood DB, app_user, auth_user, run migrations 0001–0005

- [ ] 2. Create the `tood` database if it does not exist, then run `scripts/migrate.py`
         which idempotently creates `app_user`, `auth_user`, and applies migrations 0001–0005.
         Do not manually CREATE/ALTER roles; `ensure_roles()` in `migrate.py` handles that.
         Files: none (uses existing `migrations/*.sql` and `scripts/migrate.py`).
         Verify:
         ```
         python scripts/migrate.py
         ```
         Expected output ends with `migrations complete`. All five lines `apply  000N_*.sql`
         (or `skip   000N_*.sql` if already applied). Any SQL error must be printed and execution
         must stop — do not skip a failed migration.

---

## Phase 3 — Google OAuth backend (FastAPI)

### 3a. Add new dependencies

- [ ] 3. Add `itsdangerous>=2.2` and `httpx>=0.27` to `[project.dependencies]` in
         `apps/api/pyproject.toml`. `httpx` is already a dev dep; move it to main deps.
         `itsdangerous` is new.
         **Decision:** Pin to `itsdangerous>=2.2` (current stable; URLSafeTimedSerializer
         signature API stable since 2.0).
         Files: `apps/api/pyproject.toml`
         Verify: `cd apps/api && pip install -e ".[dev]" -q && python -c "import itsdangerous, httpx; print('ok')`
         Expected: prints `ok`.

### 3b. Add OAuth config fields to Settings

- [ ] 4. Add the following fields to the `Settings` class in `apps/api/app/core/config.py`:
         ```python
         google_client_id: str = ""
         google_client_secret: str = ""
         google_redirect_uri: str = "https://tood.uk/auth/google/callback"
         session_secret: str = "change-me-in-production"
         ```
         Do not log or expose these fields anywhere. `google_redirect_uri` default is the
         canonical production value; local dev overrides via `.env`.
         Files: `apps/api/app/core/config.py`
         Verify: `cd apps/api && python -c "from app.core.config import settings; print(settings.google_redirect_uri)"`
         Expected: `https://tood.uk/auth/google/callback`.

### 3c. Migration 0006 — user_sessions and oauth_accounts tables

- [ ] 5. Create `migrations/0006_oauth.sql` with the following schema.
         **Design decisions:**
         - `user_sessions` uses `auth_user` role (identity data, not tenant data) — consistent with `api_tokens`.
         - `oauth_accounts` links a Google `sub` to an existing `users` row; avoids duplicating users.
         - Session token stored as SHA-256 hash — same pattern as `api_tokens` (never store raw token).
         - `expires_at` column enforces TTL at query time; background cleanup not required for MVP.
         - No RLS weakening: `user_sessions` and `oauth_accounts` are identity tables managed by `auth_user`, same grant pattern as `api_tokens`.

         ```sql
         -- OAuth accounts: links Google identity to a TOOD user
         CREATE TABLE oauth_accounts (
           id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
           user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
           provider text NOT NULL DEFAULT 'google',
           provider_sub text NOT NULL,          -- Google "sub" claim
           email text NOT NULL,
           created_at timestamptz NOT NULL DEFAULT now(),
           UNIQUE (provider, provider_sub)
         );
         ALTER TABLE oauth_accounts ENABLE ROW LEVEL SECURITY;
         ALTER TABLE oauth_accounts FORCE ROW LEVEL SECURITY;
         CREATE POLICY oauth_identity ON oauth_accounts TO auth_user USING (true) WITH CHECK (true);
         GRANT SELECT, INSERT, DELETE ON oauth_accounts TO auth_user;

         -- Server-side sessions: token stored as SHA-256 hash, never raw
         CREATE TABLE user_sessions (
           id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
           user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
           org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
           role text NOT NULL,
           token_hash char(64) NOT NULL UNIQUE,
           expires_at timestamptz NOT NULL,
           created_at timestamptz NOT NULL DEFAULT now()
         );
         ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
         ALTER TABLE user_sessions FORCE ROW LEVEL SECURITY;
         CREATE POLICY session_identity ON user_sessions TO auth_user USING (true) WITH CHECK (true);
         GRANT SELECT, INSERT, DELETE ON user_sessions TO auth_user;
         ```

         Files: `migrations/0006_oauth.sql`
         Verify: `python scripts/migrate.py`
         Expected: `apply  0006_oauth.sql` printed, `migrations complete`. Stop and report any error.

### 3d. OAuth helper module

- [ ] 6. Create `apps/api/app/core/oauth.py` implementing these four functions:

         **`make_state(email_hint: str | None) -> str`**
         Uses `itsdangerous.URLSafeTimedSerializer(settings.session_secret)` to sign a dict
         `{"ts": time.time(), "hint": email_hint or ""}`. Returns the signed string.
         Max age for verification: 600 seconds.

         **`verify_state(state: str) -> dict`**
         Calls `serializer.loads(state, max_age=600)`. Raises `HTTPException(400, "invalid state")`
         on `BadSignature` or `SignatureExpired`.

         **`exchange_code(code: str) -> dict`**
         POSTs to `https://oauth2.googleapis.com/token` with `httpx.Client` (not async — stays
         consistent with the rest of the codebase which uses sync psycopg).
         Params: `code`, `client_id`, `client_secret`, `redirect_uri`, `grant_type=authorization_code`.
         `redirect_uri` must come from `settings.google_redirect_uri` — never hardcoded.
         Returns the parsed JSON. Raises `HTTPException(502, "google token exchange failed")` on error.
         **Never log `client_secret` or `access_token`.**

         **`get_userinfo(access_token: str) -> dict`**
         GETs `https://www.googleapis.com/oauth2/v3/userinfo` with `Authorization: Bearer <token>`.
         Returns parsed JSON. Raises `HTTPException(502, "userinfo fetch failed")` on error.
         **Never log `access_token` or any response field named `sub`.**

         Files: `apps/api/app/core/oauth.py`
         Verify: `cd apps/api && python -c "from app.core.oauth import make_state, verify_state; print(verify_state(make_state(None)))"`
         Expected: dict with `ts` and `hint` keys, no exception.

### 3e. Four OAuth routes

- [ ] 7. Create `apps/api/app/routes_oauth.py` with a router at `prefix="/v1/auth"`.
         Follow the same import/style pattern as `routes.py`.

         **`GET /v1/auth/google`** — initiate OAuth
         1. Calls `make_state(None)`.
         2. Builds Google auth URL:
            `https://accounts.google.com/o/oauth2/v2/auth` with params:
            `client_id`, `redirect_uri=settings.google_redirect_uri`,
            `response_type=code`, `scope=openid email profile`, `state=<state>`,
            `access_type=offline`, `prompt=select_account`.
         3. Returns `{"auth_url": "<url>"}` — **does not redirect**; the Next.js frontend
            drives the redirect so the `X-Frame-Options` / CORS story is clean.
         Returns: `{"auth_url": str}`.

         **`GET /v1/auth/google/callback`** — handle Google redirect
         This is the route Google calls. Query params: `code`, `state`, `error` (optional).
         1. If `error` param present: raise `HTTPException(400, error)`.
         2. Call `verify_state(state)` — raises 400 on invalid/expired.
         3. Call `exchange_code(code)` to get `access_token`.
         4. Call `get_userinfo(access_token)` to get `{sub, email, name}`.
         5. Look up `oauth_accounts` by `(provider='google', provider_sub=sub)` using `auth_database_url`.
            - If found: load `user_id`, then load membership to get `org_id` and `role`.
            - If not found: create new `users` row + `oauth_accounts` row + `organisations` row +
              `memberships` row (role=`owner`) via `auth_database_url`. Then call
              `audit.record()` inside `tenant_connection()` for `account.created`.
         6. Create session: `token = secrets.token_urlsafe(32)`,
            `token_hash = hashlib.sha256(token.encode()).hexdigest()`,
            insert into `user_sessions` (expires 30 days, use `auth_database_url`).
         7. Redirect to `/dashboard?session_token=<raw_token>` — Next.js stores it in
            `sessionStorage` (not a cookie, to avoid CSRF surface for MVP).
         **Never log `token`, `access_token`, `sub`, or `email` at any log level.**
         Returns: `RedirectResponse` to `/dashboard?session_token=<token>`.

         **`GET /v1/auth/session`** — validate a session token
         Header: `Authorization: Bearer <session_token>`.
         1. Hash the token.
         2. Query `user_sessions` where `token_hash = %s AND expires_at > now()`.
         3. If not found: `HTTPException(401, "session expired or invalid")`.
         4. Return `{"user_id", "org_id", "role", "expires_at"}`.
         **Never log the raw token.**
         Returns: `{"user_id": str, "org_id": str, "role": str, "expires_at": str}`.

         **`POST /v1/auth/logout`** — invalidate session
         Header: `Authorization: Bearer <session_token>`.
         1. Hash the token.
         2. DELETE from `user_sessions` where `token_hash = %s`.
         3. Return `{"ok": true}`.
         Returns: `{"ok": bool}`.

         Files: `apps/api/app/routes_oauth.py`
         Verify: `cd apps/api && python -c "from app.routes_oauth import oauth_router; print(len(oauth_router.routes))"` — expected: `4`.

### 3f. Register OAuth router in main.py

- [ ] 8. In `apps/api/app/main.py`, add:
         ```python
         from app.routes_oauth import oauth_router
         app.include_router(oauth_router)
         ```
         Place this after the existing `app.include_router(admin_router)` line.
         Files: `apps/api/app/main.py`
         Verify: `cd apps/api && python -c "from app.main import app; paths = [r.path for r in app.routes]; print([p for p in paths if '/auth/' in p])"`
         Expected: list contains `/v1/auth/google`, `/v1/auth/google/callback`, `/v1/auth/session`, `/v1/auth/logout`.

---

## Phase 4 — Next.js frontend

### 4a. next.config.ts — add OAuth callback rewrite

- [ ] 9. Add a second rewrite rule to `apps/web/next.config.ts` so that
         `/auth/google/callback` (the URL Google redirects to) is proxied to the FastAPI backend.
         The existing `/api/:path*` rewrite stays untouched.
         ```ts
         {
           source: "/auth/google/callback",
           destination: `${process.env.API_URL ?? "http://localhost:8000"}/v1/auth/google/callback`,
         },
         ```
         Add it as the **first** entry in the array (before `/api/:path*`) so Next.js matches
         it before the catch-all. This is necessary because `/auth/google/callback` does not
         start with `/api/`.
         Files: `apps/web/next.config.ts`
         Verify: `cd apps/web && npm run build 2>&1 | tail -5`
         Expected: build completes with no TypeScript or config errors.

### 4b. Login page

- [ ] 10. Create `apps/web/app/login/page.tsx` — a "Sign in with Google" page.
          **Design:** Server component with a client island for the button. Style matches the
          existing dark palette (`bg-[#0F172A]`, `text-white`, blue `#3B82F6` button) from
          `page.tsx` and `dashboard/page.tsx`.

          Behaviour:
          1. On mount (client), check `sessionStorage.getItem("tood_session")`. If present,
             redirect to `/dashboard` (user is already logged in).
          2. "Sign in with Google" button: on click, fetches `GET /api/auth/google` (proxied
             to `/v1/auth/google`), gets `{"auth_url": ...}`, then sets
             `window.location.href = auth_url` to trigger the Google redirect.
          3. Show a spinner while the fetch is in progress.
          4. On error, show an inline message: "Sign-in is temporarily unavailable. Please try again."

          The page must not log or expose any token.

          Files: `apps/web/app/login/page.tsx`
          Verify: `cd apps/web && npm run build`
          Expected: build passes, no TypeScript errors.

### 4c. Dashboard auth guard and session handling

- [ ] 11. Update `apps/web/app/dashboard/page.tsx` to:
          1. On mount (client), read `sessionStorage.getItem("tood_session")`.
             - If missing: redirect to `/login`.
             - If present but came from `?session_token=<token>` in the URL (the callback
               redirect): store it with `sessionStorage.setItem("tood_session", token)`, then
               remove the query param from the URL with `history.replaceState`.
          2. Call `GET /api/auth/session` with `Authorization: Bearer <token>` to validate.
             - On 401: clear `sessionStorage` and redirect to `/login`.
             - On success: show user email / org in the dashboard header.
          3. Add a "Sign out" button that calls `POST /api/auth/logout`, clears
             `sessionStorage`, and redirects to `/login`.
          4. Preserve the existing placeholder content below the header.

          **Never** write the token to `localStorage`, a cookie, or a console log.

          Files: `apps/web/app/dashboard/page.tsx`
          Verify: `cd apps/web && npm run build`
          Expected: build passes, no TypeScript errors.

### 4d. Update Navbar "Sign in" link

- [ ] 12. In `apps/web/app/page.tsx`, change both occurrences of `href="/dashboard"` on the
          "Sign in" link (desktop nav + mobile nav) to `href="/login"`.
          This ensures unauthenticated visitors land on the login page, not the dashboard.
          Files: `apps/web/app/page.tsx`
          Verify: `cd apps/web && npm run build`
          Expected: build passes.

---

## Phase 5 — Environment variables

- [ ] 13. Update `.env` to add placeholder lines for the new OAuth variables.
          **Never put real secrets here; the file already has the correct `GCP_CLIENT_ID` /
          `GCP_CLIENT_SECRET` values which must stay, but must not be committed.**

          Add at the end of `.env` (the file is already gitignored):
          ```
          # Google OAuth — must match Google Cloud Console exactly
          GOOGLE_CLIENT_ID=<same value as GCP_CLIENT_ID above>
          GOOGLE_CLIENT_SECRET=<same value as GCP_CLIENT_SECRET above>
          GOOGLE_REDIRECT_URI=https://tood.uk/auth/google/callback
          SESSION_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
          ```

          The `config.py` `Settings` fields (`google_client_id`, `google_client_secret`,
          `google_redirect_uri`, `session_secret`) map to these env vars via pydantic-settings
          automatic lowercasing.

          Verify `.env.example` exists and contains the same keys with placeholder values
          (no real values). If `.env.example` does not exist, create it with:
          ```
          GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
          GOOGLE_CLIENT_SECRET=your-client-secret
          GOOGLE_REDIRECT_URI=https://tood.uk/auth/google/callback
          SESSION_SECRET=generate-with-python-secrets
          ```

          Files: `.env` (runtime values, never committed), `.env.example` (placeholders, safe to commit)
          Verify: `cd apps/api && python -c "from app.core.config import settings; assert settings.google_redirect_uri == 'https://tood.uk/auth/google/callback', settings.google_redirect_uri; print('redirect_uri ok')"`
          Expected: `redirect_uri ok`.

---

## Phase 6 — Run all tests

- [ ] 14. Run the full pytest suite. All existing tests must continue to pass.
          The new OAuth routes must not break `test_health.py`, `test_api_security.py`,
          `test_tenant_isolation.py`, `test_append_only.py`, `test_provenance_hash.py`,
          `test_residency_guard.py`, or `test_workflow.py`.
          Files: none (read-only verification step)
          Verify:
          ```
          cd apps/api && pytest -q
          ```
          Expected: all tests pass. If any test that previously passed now fails, stop and
          report; do not modify the test to make it pass.

- [ ] 15. Run ruff linter on the API.
          Files: none
          Verify:
          ```
          cd apps/api && ruff check .
          ```
          Expected: zero errors. Fix any lint errors in the files introduced in this plan before
          marking this item done.

- [ ] 16. Run the Next.js production build.
          Files: none
          Verify:
          ```
          cd apps/web && npm run build
          ```
          Expected: build completes with exit code 0.

- [ ] 17. Manual curl smoke test of the OAuth initiation endpoint.
          Start the API: `cd apps/api && uvicorn app.main:app --port 8000`
          Then in a second terminal:
          ```
          curl -s http://localhost:8000/v1/auth/google | python -m json.tool
          ```
          Expected: JSON with key `auth_url` whose value starts with
          `https://accounts.google.com/o/oauth2/v2/auth` and contains
          `redirect_uri=https%3A%2F%2Ftood.uk%2Fauth%2Fgoogle%2Fcallback` (URL-encoded).
          Verify the `state` parameter is present and non-empty.
          Stop and report if `auth_url` is missing or `redirect_uri` does not match exactly.

---

## Phase 7 — Commit and push

- [ ] 18. Stage and commit all changes on branch `feature/saas-platform`.
          If the branch does not exist locally, create it:
          ```
          git checkout -b feature/saas-platform
          ```
          Stage only the files changed in this plan:
          ```
          git add \
            migrations/0006_oauth.sql \
            apps/api/app/core/oauth.py \
            apps/api/app/core/config.py \
            apps/api/app/routes_oauth.py \
            apps/api/app/main.py \
            apps/api/pyproject.toml \
            apps/web/next.config.ts \
            apps/web/app/login/page.tsx \
            apps/web/app/dashboard/page.tsx \
            apps/web/app/page.tsx \
            .env.example
          ```
          **Do not stage `.env` — it contains real credentials.**
          Verify no secrets appear in `git diff --cached` before committing.

          Commit message:
          ```
          feat: Google OAuth login, user_sessions table, dashboard auth guard (section 19)

          - Add migration 0006_oauth.sql: oauth_accounts + user_sessions tables
          - Add app/core/oauth.py: state signing, token exchange, userinfo fetch
          - Add app/routes_oauth.py: GET /v1/auth/google, callback, session, logout
          - Update config.py: google_client_id/secret/redirect_uri, session_secret
          - Update next.config.ts: /auth/google/callback rewrite
          - Add apps/web/app/login/page.tsx: Google sign-in page
          - Update dashboard/page.tsx: session guard, logout, user display
          - Add .env.example: OAuth placeholder variables

          GOOGLE_REDIRECT_URI pinned to https://tood.uk/auth/google/callback.
          Secrets never logged. RLS, append-only triggers, hash chain untouched.
          Tests: pytest -q passed, ruff clean, next build passed.

          Agent: Kiro 1.0
          ```

          Push:
          ```
          git push -u origin feature/saas-platform
          ```
          Files: none (git operation only)
          Verify: `git log --oneline -1` shows the commit. `git status` shows clean working tree.

---

## Dependency order summary

```
1 (Cloud SQL connectivity)
  └─ 2 (migrations 0001-0005)
       └─ 3 (add itsdangerous/httpx)
            └─ 4 (config.py fields)
                 └─ 5 (migration 0006)
                      └─ 6 (oauth.py helper)
                           └─ 7 (routes_oauth.py)
                                └─ 8 (register router)
                                     ├─ 9  (next.config.ts rewrite)
                                     ├─ 10 (login page)
                                     ├─ 11 (dashboard guard)
                                     └─ 12 (navbar link)
                                          └─ 13 (env vars)
                                               └─ 14-17 (all tests)
                                                    └─ 18 (commit + push)
```

Items 9–12 are independent of each other (all depend on item 8 being done).

---

## Assumptions and notes

1. **Cloud SQL password**: The exact `gcloud` command to reset the password will depend on
   the Cloud SQL instance name. The implementer should run:
   `gcloud sql instances list` to find the instance name, then
   `gcloud sql users set-password postgres --instance=<INSTANCE> --password=<NEW_PASSWORD>`.
   Update `DATABASE_ADMIN_URL` in `.env` with the new password. Never commit it.

2. **itsdangerous not in current deps**: `itsdangerous>=2.2` must be added to `pyproject.toml`
   main dependencies (not just dev). The virtual environment must be reinstalled after this change.

3. **`httpx` promotion**: `httpx` is currently in `[project.optional-dependencies].dev`. Move
   it to `[project.dependencies]` so it is available in production.

4. **No async in oauth.py**: The rest of the API uses synchronous `psycopg.connect()`.
   `httpx.Client` (sync) is consistent with that pattern. Do not use `httpx.AsyncClient`.

5. **Session token in URL query string**: Passing the token in the redirect URL is a pragmatic
   MVP choice — it is HTTPS-only and Next.js removes it from the URL immediately with
   `history.replaceState`. A `Set-Cookie: HttpOnly; Secure; SameSite=Lax` approach is more
   secure for production and should be a follow-up task.

6. **No Google Secret Manager in this plan**: The task asks for "Secret Manager placeholders".
   This plan adds `.env.example` with placeholder variable names. Secret Manager configuration
   (`gcloud secrets create`) is an infrastructure task outside the code change and is noted
   here as a follow-up: each variable (`GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`,
   `STRIPE_SECRET_KEY`) should become a Secret Manager secret referenced by the Cloud Run
   service account.
