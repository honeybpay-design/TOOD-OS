# TOOD — Trusted Operations & Organised Documents

> AI-assisted bid writing · Built for UK Public Sector Procurement

![Tests](https://img.shields.io/badge/tests-44%20passed-brightgreen)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-16.4.0-black)
![Cloud Run](https://img.shields.io/badge/cloud-run-europe--west2-4285F4)
![License](https://img.shields.io/badge/license-MIT-green)

TOOD is a multi-tenant SaaS platform that helps UK public-sector suppliers write compliant tender responses. It extracts requirements verbatim from tender documents, generates AI-drafted answers grounded in an approved evidence library, and enforces a named human approval step before any export — no bid is ever submitted automatically. The platform is aligned with the Procurement Act 2023, PPN 01/17, and PPN 02/24.

---

## Live

| Service | URL |
|---|---|
| Website | https://tood.uk |
| API (Cloud Run) | https://tood-os-api-844874461521.europe-west2.run.app |
| API docs (Swagger) | https://tood-os-api-844874461521.europe-west2.run.app/docs |
| Web app (Cloud Run) | https://tood-os-web-844874461521.europe-west2.run.app |

**Compliance frame:** Procurement Act 2023 · PPN 01/17 · PPN 02/24

---

## What it does

- **Requirement extraction (verbatim, source-referenced)** — parses uploaded tender documents (PDF, DOCX, plain text up to 20 MB) and extracts requirements word-for-word, each with a reference to its source document, page, and block. A verbatim check discards any candidate whose text cannot be confirmed in the source block.
- **Evidence-based AI drafting (Gemini 2.5 Pro via Vertex AI)** — draft answers are generated using only items from the organisation's approved evidence library. Every AI-generated segment is tagged with the evidence it drew from. Evidence not explicitly approved by a bid manager cannot be used.
- **Claim verification against approved evidence library** — after drafting or editing, every factual claim (numbers, certifications, statistics) is checked against approved evidence. Unsupported claims are flagged and block export until acknowledged by a named bid manager or removed.
- **Named human approval workflow (no auto-submit)** — no draft can be included in an export until a named person with `bid_manager` role or above explicitly approves it. Approvals are tied to a specific revision hash.
- **Gated Word (.docx) export** — export is blocked unless every question has a latest approved draft, every unsupported claim is acknowledged, and no draft exceeds its word limit. The export file's SHA-256 hash is recorded.
- **Hash-chained audit trail (append-only)** — every draft revision and user action is stored with a hash chain. Database triggers enforce that audit records can never be updated or deleted.
- **Multi-tenant with forced Row-Level Security** — all tenant queries run through `tenant_connection()`, which sets tenant context locally to the transaction. The database enforces RLS on all tenant tables — a bug in application code cannot return cross-tenant data.
- **Stripe billing (3 plans)** — Starter £99/mo, Professional £299/mo, Enterprise £799/mo. Subscription lifecycle is managed via Stripe Checkout and webhooks.
- **Google OAuth login (configured; not yet tested in production)** — server-side OAuth 2.0 flow implemented; session tokens stored as SHA-256 hashes. Full production test pending.

---

## Quick start (local)

**Prerequisites:** Docker Desktop, Python 3.12, Node 20

```bash
git clone <repo>
cd tood.com

# Start database
docker compose up -d --wait

# Apply migrations
python scripts/migrate.py

# Verify installation (must print 17/17 checks passed)
python scripts/verify_install.py

# Run API tests (must print 44 passed)
cd apps/api && pytest -q
```

---

## Architecture

| Layer | Technology | Version |
|---|---|---|
| API | FastAPI (Python), modular monolith | ≥0.115 |
| Runtime | Python | 3.12 |
| Frontend | Next.js (standalone output) | 16.4.0 |
| UI runtime | React | 19.3.0 |
| Database | PostgreSQL 16 with pgvector | pg16 |
| AI | Gemini 2.5 Pro via Vertex AI (europe-west2) | — |
| AI fallback | Gemini 2.0 Flash, then local template provider | — |
| Containerisation | Docker / Docker Compose | — |
| CI/CD | GitHub Actions | — |
| Deployment | Google Cloud Run (europe-west2) | — |
| Hosting | Firebase Hosting → Cloud Run rewrites | — |
| Payments | Stripe | ≥10.0 |
| GCP Project | `tood-os` | — |

All AI calls are routed exclusively through `app/ai_gateway`. Business code never imports a vendor AI SDK directly. A residency guard (`app/ai_gateway/residency.py`) enforces that AI calls are only made to approved European regions.

---

## API

Base URL: `https://tood-os-api-844874461521.europe-west2.run.app`

Interactive docs: `/docs`

All endpoints except `/v1/signup`, `/healthz`, `/readyz`, and `/v1/billing/webhook` require a `Bearer <token>` header or `X-Session-Token` header.

### Accounts

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/signup` | Create organisation and first user; returns API token |
| `GET` | `/v1/me` | Current user, org, role, and active AI provider |

### Tenders

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/tenders` | Create a tender (bid_manager+) |
| `GET` | `/v1/tenders` | List tenders with requirement and question counts |
| `POST` | `/v1/tenders/{id}/documents` | Upload and parse a tender document |
| `GET` | `/v1/tenders/{id}/requirements` | List verbatim extracted requirements |
| `GET` | `/v1/tenders/{id}/questions` | List questions derived from requirements |
| `GET` | `/v1/tenders/{id}/readiness` | Export readiness check — lists all blocking problems |
| `GET` | `/v1/tenders/{id}/export` | Export approved answers as a Word .docx (bid_manager+) |

### Evidence

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/evidence` | Add an evidence item (contributor+) |
| `GET` | `/v1/evidence` | List evidence items |

### Drafts

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/questions/{id}/drafts` | Generate an AI draft for a question (contributor+) |
| `GET` | `/v1/drafts/{id}` | Get a draft with claims, word count, approval status |
| `PATCH` | `/v1/drafts/{id}` | Edit a draft (creates a new version) |
| `POST` | `/v1/drafts/{id}/approve` | Approve a draft (bid_manager+; named person only) |
| `GET` | `/v1/drafts/{id}/provenance` | Hash chain, revision list, AI-retained ratio |

### Audit

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/audit` | Audit log with hash chain verification (admin+) |

### Billing

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/billing/checkout` | Create a Stripe Checkout session |
| `GET` | `/v1/billing/status` | Current plan, subscription status, usage vs limits |

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/google/login` | Initiate Google OAuth — returns redirect URL |
| `GET` | `/v1/auth/google/callback` | Google OAuth callback; creates session token |
| `GET` | `/v1/auth/session` | Validate a session token |
| `POST` | `/v1/auth/logout` | Invalidate a session token |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/healthz` | Liveness check |
| `GET` | `/readyz` | Readiness check (database ping) |

---

## Pricing

| Plan | Price | Tenders | Users | AI provider |
|---|---|---|---|---|
| Starter | £99/mo | 3 | 2 | Template (local, no external AI) |
| Professional | £299/mo | 20 | 10 | Gemini 2.5 Pro |
| Enterprise | £799/mo | Unlimited | Unlimited | Gemini 2.5 Pro |

Subscription billing is managed via Stripe Checkout. Plan limits are enforced in `app/services/billing.py`.

---

## Compliance

### Procurement Act 2023
The Procurement Act 2023 replaces the Public Contracts Regulations 2015 as the primary framework for UK public procurement. TOOD helps suppliers structure responses that meet the updated evaluation criteria and transparency obligations. Requirement extraction ensures that tender questions are addressed verbatim, and the gated export ensures that every submitted answer has been explicitly reviewed and approved.

### PPN 01/17 — Social Value
Policy Procurement Note 01/17 requires that social value be evaluated in procurement decisions. TOOD's evidence library model ensures that social value claims included in bid responses are sourced from actual approved evidence items, not generated without a factual basis. Unapproved or unsupported claims are flagged before export.

### PPN 02/24 — AI in Procurement
PPN 02/24 requires that AI use in procurement is transparent, human-supervised, and auditable. TOOD addresses this through three mechanisms: (1) named approval — a human with bid_manager role must explicitly approve every draft; (2) a hash-chained audit log recording every action and every draft revision; and (3) a hard rule that no bid is ever submitted automatically under any circumstances.

---

## Development

### Prerequisites

- Python 3.12+
- Node 20+
- Docker Desktop

### Run tests

```bash
cd apps/api && pytest -q
# Expected: 44 passed, 0 failed, 0 skipped
```

### Lint

```bash
cd apps/api && ruff check .
# Expected: All checks passed! (0 violations)
```

### Apply migrations

```bash
python scripts/migrate.py
```

### Run API locally

```bash
cd apps/api && uvicorn app.main:app --reload --port 8000
```

### Run frontend locally

```bash
cd apps/web && npm run dev
```

---

## Deployment

### Cloud Run

Both the API and the web app are deployed to Google Cloud Run in `europe-west2`. The deploy script handles building and pushing container images via Artifact Registry and deploying the Cloud Run services.

```bash
bash scripts/deploy.sh
```

Service definitions are in `infra/cloudrun/api.yaml` and `infra/cloudrun/web.yaml`.

The CI/CD `deploy` job in `.github/workflows/ci.yml` runs automatically on merge to `main`, using GCP Workload Identity Federation.

### Firebase Hosting

The `tood.uk` domain is served via Firebase Hosting, which rewrites `/v1/**` and `/healthz` to the API Cloud Run service and all other traffic to the web Cloud Run service.

```bash
firebase deploy --only hosting
```

---

## Documentation

- [System Overview](docs/SYSTEM_OVERVIEW.md)
- [User Guide](docs/USER_GUIDE.md)
- [Technical Handover](docs/TECHNICAL_HANDOVER.md)

---

## Known limitations

- **Google OAuth configured but not yet tested in production** — the server-side OAuth 2.0 flow is implemented and migration 0006 is applied locally, but the full redirect → Google consent → callback flow has not been exercised against the live deployment. Test in staging before enabling for end users.
- **Cloud SQL instance in `us-east4`, not `europe-west2`** — the Vertex AI region is correctly set to `europe-west2` for UK data residency, but the Cloud SQL instance (`tood-os-instance`) is provisioned in `us-east4`. This is a data residency gap that should be reviewed before production.
- **No malware scanner on file uploads** — uploaded documents are parsed and stored but no malware scanning step runs. The upload response explicitly notes this. A scanner should be configured before production use.
- **CI deploy job runs only on merge to `main`; PRs do not auto-deploy** — the `deploy` job in `ci.yml` is gated on `github.ref == 'refs/heads/main'` and `github.event_name == 'push'`.

---

## Version

v0.2.0 — 2026-10-15

---

© 2026 Honey B2024 Ltd — Registered in England
