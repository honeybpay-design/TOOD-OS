# TOOD — Technical Handover

Version: 0.2.0 | Date: 2026-10-13
Branch: `feature/saas-platform` (pending merge to main)

---

## Architecture Overview

TOOD is a multi-tenant SaaS platform consisting of:

- **FastAPI monolith** (`apps/api`) — Python 3.12, all business logic, REST API
- **Next.js 16 frontend** (`apps/web`) — React 19, server-side rendering, client-side dashboard
- **PostgreSQL 16** with pgvector extension — Cloud SQL instance `tood-os-instance` (currently `us-east4`; see Known Issues)
- **Vertex AI Gemini 2.5 Pro** — drafting model, GCP project `tood-os`, region `europe-west2`
- **Google Cloud Run** — target deployment platform, `europe-west2`
- **Stripe** — subscription billing

---

## Repository Layout

```
apps/api/             FastAPI application
  app/
    main.py           App entry point, middleware, health endpoints
    routes.py         All /v1/* API routes + /admin/* routes
    routes_oauth.py   OAuth routes (/v1/auth/*)
    core/
      auth.py         Token authentication, Ctx dataclass, role enforcement
      config.py       Settings (pydantic-settings, reads .env)
      oauth.py        Google OAuth state signing, token exchange, userinfo
      audit.py        Audit event recording and chain verification
      monitoring.py   Google Cloud Monitoring integration
      tenant.py       tenant_connection() — RLS-safe connection factory
    ai_gateway/
      provider.py     get_provider(), TemplateProvider, Segment dataclass
      gemini_provider.py  GeminiProvider via Vertex AI
      agent.py        ToodAgent: extract, draft, verify orchestration
      saas_agent.py   SaaSAgent: platform metrics, health, quota monitoring
      residency.py    Residency guard — enforces AI_ALLOWED_REGIONS
    provenance/
      hashchain.py    Hash chain: compute_hash, verify_chain, Revision
    services/
      billing.py      Stripe billing: checkout, webhook, plan limits
      drafting.py     Draft text processing, claim verification, word count
      export.py       build_docx() — Word document generation
      parsing.py      PDF/DOCX/text parsing, sniff(), parse()
      requirements.py Requirement candidate extraction, verbatim check
      storage.py      ObjectStore protocol, LocalStore implementation
    static/           Static files served at /ui/

apps/web/             Next.js frontend
  app/
    page.tsx          Landing page (compliance strip, hero, PPN section, demo)
    layout.tsx        Root layout, fonts, global CSS
    login/page.tsx    Sign in with Google page
    dashboard/page.tsx  Session-guarded dashboard
    admin/page.tsx    Admin metrics page
  next.config.ts      API proxy rewrites (/api/* → /v1/*, /auth/google/callback)

migrations/           SQL migrations (apply with scripts/migrate.py)
  0001_schema.sql
  0002_security.sql
  0003_tokens_and_audit_rls.sql
  0004_ordering.sql
  0005_billing.sql
  0006_oauth.sql

scripts/              Utility scripts
  bootstrap.ps1 / bootstrap.sh   Full local setup
  migrate.py          Applies pending migrations
  verify_install.py   17-check verification suite
  deploy.sh           Cloud Run deploy script
  admit_model.py      Model Admission Test
  demo.py             End-to-end demo run

infra/cloudrun/       Cloud Run service definitions
  api.yaml
  web.yaml

docs/                 Documentation
prompts/              Versioned AI prompts
rules/                Versioned compliance rules
evals/                Golden set and evaluation thresholds
security/             Threat model
```

---

## API Modules

All routes require a Bearer token or X-Session-Token header unless noted.

### /v1/* (main router)

| Method | Path | Minimum role | Description |
|---|---|---|---|
| POST | /v1/signup | — (public, allow_signup flag) | Create organisation + first user, returns API token |
| GET | /v1/me | any authenticated | Current user, org, role, AI provider |
| POST | /v1/tenders | bid_manager | Create a tender |
| GET | /v1/tenders | any authenticated | List tenders with counts |
| POST | /v1/tenders/{id}/documents | bid_manager | Upload and parse a document |
| GET | /v1/tenders/{id}/requirements | any authenticated | List extracted requirements |
| GET | /v1/tenders/{id}/questions | any authenticated | List questions |
| GET | /v1/tenders/{id}/readiness | any authenticated | Export readiness check |
| GET | /v1/tenders/{id}/export | bid_manager | Export approved answers as .docx |
| POST | /v1/evidence | contributor | Add evidence item |
| POST | /v1/evidence/{id}/approve | bid_manager | Approve evidence item |
| GET | /v1/evidence | any authenticated | List evidence |
| POST | /v1/questions/{id}/drafts | contributor | Generate AI draft |
| GET | /v1/drafts/{id} | any authenticated | Get draft |
| PATCH | /v1/drafts/{id} | contributor | Edit draft (creates new version) |
| POST | /v1/claims/{id}/acknowledge | bid_manager | Acknowledge unsupported claim |
| POST | /v1/drafts/{id}/approve | bid_manager | Approve draft |
| GET | /v1/drafts/{id}/provenance | any authenticated | Hash chain and AI ratio |
| GET | /v1/audit | admin | Audit log with chain verification |
| POST | /v1/billing/checkout | any authenticated | Create Stripe checkout session |
| POST | /v1/billing/webhook | — (Stripe signature) | Process Stripe webhook events |
| GET | /v1/billing/status | any authenticated | Current plan, limits, usage |

### /v1/auth/* (oauth router)

| Method | Path | Description |
|---|---|---|
| GET | /v1/auth/google | Initiate Google OAuth login |
| GET | /v1/auth/google/callback | Google redirect handler, creates session |
| GET | /v1/auth/session | Validate session token |
| POST | /v1/auth/logout | Invalidate session |

### /admin/* (admin router — requires admin role)

| Method | Path | Description |
|---|---|---|
| GET | /admin/metrics | Platform MRR, subscriptions, churn |
| GET | /admin/tenants | All orgs with usage counts |
| GET | /admin/health | DB + AI provider health |
| GET | /admin/report | Daily summary report |
| POST | /admin/tenant/{id}/plan | Force plan change for an org |

### App endpoints

| Method | Path | Description |
|---|---|---|
| GET | / | Redirect to /ui/ |
| GET | /healthz | Liveness check |
| GET | /readyz | Readiness check (DB ping) |

---

## Database

### Extensions required
- `pgvector` — vector similarity search (evidence chunks)
- `pg_trgm` — trigram full-text search
- `pgcrypto` — UUID generation

### Migrations

| File | Contents |
|---|---|
| `0001_schema.sql` | Core tables: organisations, users, memberships, api_tokens, tenders, documents, doc_blocks, requirements, questions, evidence_items, evidence_chunks, drafts, draft_claims, approvals, revisions, audit_events, daily_anchors, export_manifests |
| `0002_security.sql` | RLS policies, DB roles (app_user, auth_user), forced RLS on all tenant tables |
| `0003_tokens_and_audit_rls.sql` | RLS on api_tokens and audit_events; append-only triggers on revisions and audit_events |
| `0004_ordering.sql` | Indexes for ordering queries |
| `0005_billing.sql` | subscriptions table; stripe_customer_id on organisations; plan column |
| `0006_oauth.sql` | oauth_accounts, user_sessions tables — **PENDING on Cloud SQL** |

### Integrity guarantees (must never be weakened)
- Forced RLS on all tenant tables — queries as `app_user` can only see their tenant's rows
- Append-only triggers on `revisions`, `audit_events`, `daily_anchors` — rows can never be updated or deleted
- Hash chain in `revisions` — each row includes the previous row's hash
- Hash chain in `audit_events` — verified via `audit.verify()`

### Tenant connection
All business queries must use `tenant_connection(org_id)` from `app.core.tenant`. **Never use a plain `SET` for tenant context.** The function uses `set_config(..., true)` (local to the transaction) and connects as `app_user`.

---

## Key Dependencies and Versions

### Python (from `apps/api/pyproject.toml`)

| Package | Version |
|---|---|
| fastapi | ≥0.115 |
| uvicorn[standard] | ≥0.30 |
| psycopg[binary,pool] | ≥3.2 |
| pydantic-settings | ≥2.4 |
| pymupdf | ≥1.24 |
| python-docx | ≥1.1 |
| python-multipart | ≥0.0.9 |
| tzdata | ≥2024.1 |
| google-cloud-aiplatform | ≥1.60 |
| google-auth | ≥2.30 |
| google-cloud-monitoring | ≥2.20 |
| google-cloud-logging | ≥3.10 |
| stripe | ≥10.0 |
| httpx | ≥0.27, <1 |
| itsdangerous | ≥2.2, <3 |
| python-jose[cryptography] | ≥3.3, <4 |
| pytest | ≥8 (dev) |
| ruff | ≥0.6 (dev) |

Verified installed: FastAPI 0.143.0 (from install report).

### Node / Next.js (from `apps/web/package.json`)

| Package | Version |
|---|---|
| next | 16.4.0 |
| react | 19.3.0 |
| react-dom | 19.3.0 |
| class-variance-authority | ^0.7.1 |
| clsx | ^2.1.1 |
| lucide-react | ^1.56.0 |
| tailwind-merge | ^3.7.0 |
| tw-animate-css | ^1.4.0 |
| tailwindcss | ^4 (dev) |
| typescript | ^5 (dev) |
| eslint-config-next | 16.4.0 (dev) |

---

## Environment Variables Required

All variable **names** are listed below. No values are included here. Variables marked (Secret Manager) should be stored in Google Cloud Secret Manager in production.

| Variable | Description | Secret Manager |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection for app_user | Yes |
| `DATABASE_ADMIN_URL` | PostgreSQL connection for postgres/admin | Yes |
| `AUTH_DATABASE_URL` | PostgreSQL connection for auth_user | Yes |
| `AI_ALLOWED_REGIONS` | Comma-separated list of permitted AI regions | No |
| `AI_PROVIDER` | `template` or `gemini` | No |
| `GCP_PROJECT` | GCP project ID | No |
| `GCP_REGION` | GCP region for Vertex AI | No |
| `STORAGE_DIR` | Local disk path for uploaded files | No |
| `MAX_UPLOAD_MB` | Maximum upload file size in MB | No |
| `ALLOW_SIGNUP` | Boolean: allow public sign-up | No |
| `STRIPE_SECRET_KEY` | Stripe secret key | Yes |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | No |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | Yes |
| `STRIPE_PRICE_STARTER` | Stripe price ID for Starter plan | No |
| `STRIPE_PRICE_PROFESSIONAL` | Stripe price ID for Professional plan | No |
| `STRIPE_PRICE_ENTERPRISE` | Stripe price ID for Enterprise plan | No |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret (never logged) | Yes |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL (must match GCP console) | No |
| `SESSION_SECRET` | Secret for signing OAuth session state (min 32 bytes) | Yes |

---

## Local Development Setup

### Prerequisites
- Git
- Python 3.12+
- Node 20+
- Docker Desktop

### Bootstrap

```bash
# Windows PowerShell
./scripts/bootstrap.ps1

# macOS / Linux / WSL
./scripts/bootstrap.sh
```

Expected output: `17/17 checks passed`

### Run tests

```bash
cd apps/api
pytest -q
```

Expected: `44 passed, 0 failed, 0 skipped`

### Lint

```bash
cd apps/api
ruff check .
```

Expected: `All checks passed!`

### Run API

```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

### Run frontend

```bash
cd apps/web
npm run dev
```

---

## Deployment

### Cloud Run services

| Service | Name | Region |
|---|---|---|
| API | `tood-os-api` | `europe-west2` |
| Frontend | `tood-os-web` | `europe-west2` |

### Artifact Registry

Images are pushed to: `europe-west2-docker.pkg.dev/tood-os/tood/`

### Deploy script

`scripts/deploy.sh` — builds and pushes both API and web images using `gcloud builds submit`, then deploys both Cloud Run services using service definitions from `infra/cloudrun/api.yaml` and `infra/cloudrun/web.yaml`.

Requires `gcloud` authenticated with Workload Identity (configured in CI/CD) or a service account key.

### Manual deployment steps

```bash
bash scripts/deploy.sh
```

### DNS

DNS for `tood.uk` is managed at **Fasthosts**. Records pointing to Cloud Run services have not yet been configured. This is a pending action before the site goes live.

---

## CI/CD

CI is configured in `.github/workflows/ci.yml`. Jobs run on pull requests and pushes to `main`.

### Jobs

| Job | Triggers | Steps |
|---|---|---|
| `api` | PR + push to main | Install deps → ruff lint → migrate → verify_install (17/17) → pytest 44 tests → fail if any skipped |
| `secrets` | PR + push to main | gitleaks secret scanning on full git history |
| `web` | PR + push to main (if package.json exists) | npm ci → npm run build |
| `deploy` | Push to `main` only | GCP Workload Identity auth → gcloud setup → `bash scripts/deploy.sh` |

---

## Security Considerations

- **All AI calls through `app/ai_gateway` only.** Business code must never import a vendor AI SDK. The gateway is the only permitted path to any AI model.
- **Residency guard.** `app/ai_gateway/residency.py` checks that the provider's region is in `AI_ALLOWED_REGIONS` before any call is made. Default allowed regions: `europe-west2, europe-west1, europe-west4, eu-west-2, eu-west-1, eu-central-1, uk-south`.
- **Model Admission Test.** A new model cannot be enabled without running `scripts/admit_model.py` and recording the result. This is enforced by AGENTS.md and the blueprint (section 28).
- **RLS enforced at DB level.** Even if application code has a bug, the database will not return cross-tenant data.
- **Human review required before merge for:** authentication/RLS, migrations, billing, AI gateway, data deletion, provenance/anchoring, and anything under `security/`.
- **No bid submitted automatically.** The export gate is mandatory. No code path bypasses named approval.
- **Append-only audit.** The database triggers on `revisions`, `audit_events`, and `daily_anchors` prevent any modification or deletion of audit records.
- **Session tokens.** Stored as SHA-256 hashes in the database. The raw token is never persisted.
- **CSRF protection.** OAuth state parameter is signed with `itsdangerous.URLSafeTimedSerializer` with a 600-second maximum age.

---

## Known Issues and Pending Work

1. **Migration 0006 (OAuth) not yet applied to Cloud SQL.** The `oauth_accounts` and `user_sessions` tables do not exist on the production database. Google login will fail until this is applied: `python scripts/migrate.py` (when Cloud SQL is accessible).

2. **API Cloud Run not confirmed running.** The deploy script and service definitions exist. A successful live end-to-end API call to the deployed Cloud Run service has not been confirmed.

3. **Google OAuth not tested in production.** The full OAuth flow (redirect → Google consent → callback → session) has not been exercised against the live deployment. Test in a staging environment first.

4. **DNS for `tood.uk` not configured.** The site cannot be reached at this domain. DNS records must be configured at Fasthosts to point to Cloud Run.

5. **Cloud SQL instance in `us-east4`, not `europe-west2`.** The Vertex AI region is correctly `europe-west2`, but the database is in a US region. This is non-ideal for UK data residency. Consider migrating the Cloud SQL instance to `europe-west2` before production.

6. **No malware scanner configured for file uploads.** The upload route explicitly notes this in its response. A malware scanning step must be added to the upload path before production.

7. **Stripe webhook secret is a placeholder.** Subscription events from Stripe (plan upgrades, cancellations) will not be processed until a real `STRIPE_WEBHOOK_SECRET` is set.

8. **`on_event` deprecation in FastAPI.** `main.py` uses `@app.on_event("startup")` which is deprecated in recent FastAPI versions. Replace with `@app.lifespan` context manager. Cosmetic/non-blocking for now.

9. **Cloud SQL automated backups.** The instance is `db-f1-micro` and automated backups are not confirmed enabled. Enable before production.

---

## Backup and Recovery

- **Cloud SQL automated backups:** Not confirmed enabled on current `db-f1-micro` instance. Enable via GCP Console → Cloud SQL → `tood-os-instance` → Backups.
- **Local development:** Data is in the Docker volume `pgdata`. Back up with `docker run --rm -v pgdata:/data -v $(pwd):/backup alpine tar czf /backup/pgdata.tar.gz /data`.
- **Uploaded files:** Stored at `data/uploads/` in local development. No cloud backup configured. In production, the storage backend should be switched to GCS with versioning enabled.

---

## Version History

| Version | Date | Notes |
|---|---|---|
| v0.2.0 | 2026-10-13 | Initial install-verified + SaaS platform + Google OAuth + landing page redesign + documentation |

---

*Prepared from direct codebase inspection. Dependency versions extracted from `apps/api/pyproject.toml` and `apps/web/package.json`. Route list extracted from `apps/api/app/routes.py` and `apps/api/app/routes_oauth.py`. Environment variables extracted from `apps/api/app/core/config.py`.*
