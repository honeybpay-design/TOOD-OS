# TOOD — Trusted Operations & Organised Documents

AI-assisted tender-workflow software for UK public-sector suppliers.

> **Current status: engineering / pre-production. Production readiness has not been established.**
>
> This README describes the source tree at commit `226cbdc013060e67b43304c8336e368a25f68aab` on branch
> `delivery-2026-10-31`, plus a separately labelled Google Cloud inventory snapshot supplied from Cloud Shell
> on 31 October 2026. A component existing in source code does not prove that it is deployed, configured,
> migrated, secure in the live environment, or has passed an end-to-end test.

## Repository and release state

| Item | Observed value |
|---|---|
| Repository | [honeybpay-design/TOOD-OS](https://github.com/honeybpay-design/TOOD-OS) |
| Default branch | `main` |
| Working delivery branch | `delivery-2026-10-31` |
| Delivery commit reviewed | `226cbdc013060e67b43304c8336e368a25f68aab` |
| README status | Updated on the delivery branch; not yet merged to `main` |
| Release status | Not certified production-ready |

Do not treat this branch as deployed. The configured Cloud Build trigger described below listens for pushes to
`main`, not this delivery branch.

## What is in this repository

### Application

- **API:** FastAPI, Python 3.12+, using Psycopg to access PostgreSQL.
- **Web application:** Next.js 16.4.3, React 19.3.0.
- **Local database:** Docker Compose starts `pgvector/pgvector:pg16` for local development.
- **API client:** generated OpenAPI JSON and TypeScript declarations under `packages/api-client`.
- **Infrastructure/configuration:** Cloud Run service manifests under `infra/cloudrun/`, Firebase Hosting rewrites
  in `firebase.json`, and a Cloud Build pipeline in `cloudbuild.yaml`.

The API source contains routes and services for organisation/user access, tenders and document ingestion,
requirements and questions, evidence, draft generation and editing, review/approval, export, billing,
Google OAuth, audit, and health checks. The presence of these routes is not evidence that every journey
currently works end-to-end in the deployed environment.

### AI gateway

- Business logic obtains a provider through `apps/api/app/ai_gateway`.
- The local default provider is `template`; it is not a hosted language model.
- A Gemini adapter using the Google Gen AI SDK is present. It requires an explicit model selection and a
  valid signed model-admission receipt before model access. The adapter is configured for Vertex AI in
  `europe-west2` and rejects implicit Developer API / global-key routing.
- The deployed Cloud Run service showed an `AI_PROVIDER` environment-variable name in the supplied
  inventory, but its value and the active model-admission receipt were not provided. **Do not assume Gemini
  is currently active in production.**
- Google ADK is not listed as a dependency in the checked-in API project manifest. The current Gemini
  adapter uses `google-genai`; this repository snapshot does not establish an ADK-based agent runtime.

### Document storage

The API defines a local-disk backend and an opt-in Google Cloud Storage backend. The GCS implementation
checks the configured bucket's London location, project identity, uniform bucket-level access, public
access prevention, object generation, and content hashes.

The code supports GCS, but the supplied Cloud Run inventory does not establish the active
`STORAGE_BACKEND`, bucket name, or whether a production bucket is configured. Do not assume durable GCS
storage is active without checking the live service configuration and bucket.

### Database and migrations

- Local development uses PostgreSQL 16 with pgvector through `docker-compose.yml`.
- SQL migration files `0001` through `0016` are present.
- The API uses separate database URLs for application and authentication access.
- Tenant-scoped connection helpers set `app.org_id` transaction-locally.
- The migration files contain RLS and append-only controls. Their presence does not prove that the same
  schema, policies, grants, or triggers have been applied and verified in the live database.
- Audit V2 source and migrations are present. The V2 adapter explicitly states that it is not activated by
  import and requires a coordinated cutover. Migration `0016_revision_hash_scope.sql` labels itself
  **proposal-only** and contains guards. Do not treat Audit V2 as live or run that migration as a routine
  deployment step.

**Migration safety:** `scripts/migrate.py` loads environment configuration and applies every unapplied SQL
file in order. The runbooks record a warning that this legacy CLI is not a harmless inspection command and
can attempt database role/schema writes. Do not run it against production, and do not use
`python scripts/migrate.py --help` as a probe. A reviewed, target-locked migration procedure is required
before any real database change.

## Google Cloud inventory snapshot

The following is a transcription of the owner-supplied Cloud Shell output for project `tood-os` on
31 October 2026. It is an inventory snapshot, not a fresh live query performed by this README update.

### Cloud Run

All three listed services were in `europe-west2`:

| Service | Latest ready revision in supplied output | Service URL |
|---|---|---|
| `tood-os-api` | `tood-os-api-00036-gcq` | [API](https://tood-os-api-iiwda4phia-nw.a.run.app) |
| `tood-os-web` | `tood-os-web-00046-hp2` | [Web](https://tood-os-web-iiwda4phia-nw.a.run.app) |
| `genai-app-agentdocumentukpublicproc-1-17926831704` | `genai-app-agentdocumentukpublicproc-1-17926831704-00002-cw5` | [Agent service](https://genai-app-agentdocumentukpublicproc-1-17926831704-iiwda4phia-nw.a.run.app) |

The third service was present in the project inventory; its ownership and integration with the TOOD application
were not established by the inspected repository.

### Cloud SQL

The supplied inventory showed two RUNNABLE instances in `europe-west2`:

| Instance | Engine | State |
|---|---|---|
| `tood-os-db-london` | PostgreSQL 18 | RUNNABLE |
| `tood-os-db-pg16-london` | PostgreSQL 16 | RUNNABLE |

The supplied Cloud Run description showed the API service attached to the Cloud SQL connection
`tood-os:europe-west2:tood-os-db-london` (PostgreSQL 18 instance).

This attachment annotation does **not**, by itself, prove which database host the secret-backed
`DATABASE_URL` and `AUTH_DATABASE_URL` actually select. Their secret values were not exposed and must
not be printed. Confirm the target database using a safe, read-only runtime check before describing the
live database as PostgreSQL 18 or PostgreSQL 16.

The same supplied inventory reported no running Compute Engine VMs and no active GKE clusters.

### Firebase Hosting

The checked-in `firebase.json` declares a Hosting site named `tood-os` with these intended rewrites:

- `/v1/**`, `/healthz`, `/health`, `/readyz`, and `/docs` to Cloud Run service `tood-os-api`.
- All remaining paths to Cloud Run service `tood-os-web`.

This describes the repository configuration. The deployed Firebase Hosting configuration and current
custom-domain reachability were not independently verified during this review.

## Build and deployment paths

### Cloud Build — configured production trigger

The owner-supplied Cloud Shell output showed a Cloud Build trigger:

- Name: `deploy-main`
- Region: `europe-west2`
- Connected repository: `honeybpay-design/TOOD-OS`
- Event: push to branch matching `^main$`
- Build configuration: `cloudbuild.yaml`

The checked-in `cloudbuild.yaml` builds and pushes API and Web images to Artifact Registry in
`europe-west2`, then deploys `tood-os-api` and `tood-os-web` to Cloud Run. Therefore, a push to
`delivery-2026-10-31` does not match this trigger. A merge/push to `main` can initiate deployment.

The Cloud Shell build listing supplied for this review showed successful builds through 23 October 2026;
it did not establish a successful build for the 31 October delivery commit.

### GitHub Actions — quality workflow, not deployment

`.github/workflows/ci.yml` defines secret-scan, API, Web, and quality-gate jobs. Its final quality job
explicitly says that the workflow performs no deployment.

**Current repository blocker:** the delivery commit's Git tree does not contain the paths invoked by this
workflow:

- `scripts/test_suites/scan_secrets.py`
- `scripts/test_suites/ci_api.py`
- `scripts/test_suites/test_runner_identity.py`
- `scripts/test_suites/test_ci_policy.py`
- `security-tests/test_secret_provisioning.py`

The workflow references these paths, so the current checked-in CI definition is incomplete and cannot be
reported as passing. The delivery commit also had no GitHub Actions run or check-run result when inspected.
Do not publish a current test-pass badge or a numeric passing-test count until CI has been repaired and run.

### Deployment configuration drift — review before using legacy scripts

The checked-in `cloudbuild.yaml` deploys images using `gcloud run deploy`. The separate
`scripts/deploy.sh` uses `gcloud run services replace` with the manifests under `infra/cloudrun/`.

Those manifests do not match the supplied Cloud Run inventory:

- `infra/cloudrun/api.yaml` references Cloud SQL connection `tood-os:europe-west2:tood-db`,
  while the supplied live API annotation names `tood-os-db-london`.
- `infra/cloudrun/web.yaml` sets `API_URL=https://api.tood.uk`, while the supplied
  `cloudbuild.yaml` sets the Web service's API URL to the API's `run.app` URL.

Do not use `scripts/deploy.sh` or replace the live Cloud Run services from these manifests until the
configuration drift has been reconciled and reviewed. A service replacement can change live settings.

## Verification status and release gates

### What is evidenced

- Source files for API, Web, AI gateway, GCS storage, audit controls, and SQL migrations are present.
- API test files are present, including tests for tenant isolation, append-only behaviour, audit V2,
  provider failure, GCS storage, and Cloud Run configuration.
- A historical install report records 44 API tests passed on 13 October 2026. Other historical documents
  mention different counts. These are not current results for this delivery commit.
- The supplied Cloud Run inventory identifies ready revisions and RUNNABLE Cloud SQL instances, but does
  not prove successful user journeys or database correctness.

### Not verified for this delivery commit

- A clean installation and current complete API test run.
- GitHub Actions CI success (the referenced harness files are missing).
- Current Web lint, type-check, dependency audit, and production build results.
- Live OAuth sign-in and session lifecycle.
- Live database target, migration level, RLS policies/grants, and append-only triggers.
- Live Gemini model selection, signed admission receipt, and generation behaviour.
- GCS bucket configuration and document upload/download in the live environment.
- Billing checkout and webhook lifecycle.
- Full user journey from tender upload through extraction, evidence, drafting, approval, readiness, and export.
- Production deployment of the delivery commit.

**Release rule:** do not describe TOOD as production-ready until the missing CI harness is restored, all
required gates pass, live configuration drift is resolved, migrations are reviewed and applied through an
approved procedure, and the core user journeys pass end-to-end in a controlled staging environment.

## Developer checks

The repository contains these application-level checks; run them in a disposable local environment and
record the actual output. No result is implied by listing a command.

```powershell
# Web checks
Set-Location apps/web
npm ci
npm run lint
npx tsc --noEmit --incremental false
npm audit --audit-level=high
npm run build

# API tests (from repository root)
Set-Location ../..
Set-Location apps/api
python -m pytest -q
```

Do not point local verification or migration commands at production credentials or production data.
The current CI workflow must be repaired before these checks can be treated as the repository's release gate.

## Documentation

- [System overview](docs/SYSTEM_OVERVIEW.md)
- [Technical handover](docs/TECHNICAL_HANDOVER.md) — historical handover; check its date and branch assumptions.
- [User guide](docs/USER_GUIDE.md) — contains explicitly unverified production steps; do not treat it as proof of live behaviour.
- [Installation report](docs/install-report.md) — historical results, not a current delivery-commit test report.
- [Production readiness reports](docs/production-readiness.md) and [round 2](docs/production-readiness-2.md) — dated historical audits; their findings may be superseded.

## Accuracy and maintenance policy

1. Record the commit SHA and review date whenever this README is reconciled.
2. Separate **source present**, **configured in cloud**, **deployed**, and **verified by test**. They are different states.
3. Never infer secret values, active model IDs, database targets, successful migrations, or passing tests from variable names or configuration files alone.
4. Update the Cloud inventory only from a dated, redacted Cloud Shell export. Never include secret values, passwords, tokens, private keys, or customer data.
5. Remove obsolete claims, pricing, badges, and launch dates rather than carrying them forward without evidence.
6. Keep production changes behind a reviewed pull request and explicit human approval.

---

© 2026 Honey-B2024 Ltd
