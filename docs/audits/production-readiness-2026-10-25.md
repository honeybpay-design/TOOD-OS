# TOOD-OS Production Readiness Audit — Phase 1 (2026-10-25)

Status: **Static repository review in progress**. This report is based on inspected GitHub source files, not live cloud settings, runtime logs, database inspection, or executed tests. No claim of production readiness is made.

## Findings

### P1 — Two independent production deployment paths
- Evidence: `.github/workflows/ci.yml` defines a `deploy` job on pushes to `main`, invoking `scripts/deploy.sh`; `cloudbuild.yaml` also builds and deploys the same `tood-os-api` and `tood-os-web` Cloud Run services.
- Risk: **If both triggers are enabled**, competing releases, non-deterministic revisions, duplicated builds and unexpected rollback-like behavior.
- Important: active Cloud Build triggers and GitHub Actions execution have **not** been inspected. The existence of two definitions does not prove both execute.
- Action: inspect live Cloud Build triggers and recent GitHub Actions runs; designate one production deploy owner; make the other CI-only or explicitly manual after approval. Preserve `main` until verified.

### P1 — Cloud SQL data residency requires confirmation
- Evidence: `README.md` explicitly lists `tood-os-instance` in `us-east4`, while Cloud Run and Vertex AI are described as `europe-west2`.
- Risk: UK/EU data location expectations, transfers, privacy notices and procurement customer requirements may not match.
- Action: verify actual Cloud SQL region, backups, replicas, data flows, DPA/transfer assessment and customer promises. Do not migrate production without a separate approved plan.

### P1 — Cloud Run API target configuration drift
- Evidence: `cloudbuild.yaml` sets web `API_URL=https://tood-os-api-iiwda4phia-nw.a.run.app`, while `README.md` documents `https://tood-os-api-844874461521.europe-west2.run.app`.
- Risk: web-to-API calls could target an outdated endpoint; actual failure is **unverified**.
- Action: verify active Cloud Run service URL, web environment and routing, then centralize a validated value.

### P2 — Deployment reproducibility and mutable tags
- Evidence: `scripts/deploy.sh` builds images tagged `:latest` and replaces services using `infra/cloudrun/*.yaml`; `cloudbuild.yaml` uses commit SHA tags for its deploy.
- Risk: the two paths may deploy different images for the same source revision depending on manifest contents.
- Action: inspect manifests, use immutable image digests/commit identifiers, record deployed SHA, and add smoke checks before promotion.

### P2 — Stale setup instructions and unverified test claims
- Evidence: `README.md` uses `git clone <repo>` and `cd tood.com`, displays a Next.js 15 badge while `apps/web/package.json` pins Next.js 16.4.0, and various sections expect 44 versus 51 tests. `docs/agent-tasks.md` T05 instructs creating a Next.js app although `apps/web/package.json` already exists.
- Action: after running actual local CI, update version badges, clone path, expected test counts and agent tasks. Do not replace claimed counts with invented values.

### P2 — Security and runtime checks still required
- Evidence: `apps/api/app/main.py` includes explicit CORS origins, liveness `/healthz` and database readiness `/readyz`; `apps/api/app/ai_gateway/residency.py` checks approved provider regions.
- Limit: these files alone cannot establish end-to-end OAuth security, tenant RLS enforcement, upload malware handling, AI evidence gates or audit-chain integrity.
- Action: inspect routes, middleware, migrations, test suites and production-safe staging tests before claiming those controls are effective.

## Safe verification sequence
1. Review `AGENTS.md` and the authoritative Full Master Blueprint v1.1; preserve all non-negotiable security and approval gates.
2. Inspect Cloud Build trigger state and GitHub Actions deployment runs without changing resources.
3. Inspect `infra/cloudrun/*.yaml`, OAuth routes, tenant connections and database migrations.
4. Execute API unit/integration tests, `ruff`, frontend build/type checks, and the 17 installation checks in an isolated local/staging environment; record real outputs.
5. Conduct authorized E2E tests using synthetic tenants and documents, including OAuth redirect, upload, extraction, drafting, approval, export and cross-tenant denial.
6. Review UI accessibility, responsive behavior and real copy. Never fabricate customer logos, certifications, reviews or metrics.
7. Prepare fixes on this branch, open a PR, require human review for security/auth/RLS/billing/AI changes. **Do not merge or deploy to production without separate approval.**

## Evidence and limits
Reviewed: `AGENTS.md`, `README.md`, `cloudbuild.yaml`, `firebase.json`, `.github/workflows/ci.yml`, `scripts/deploy.sh`, `apps/web/package.json`, `apps/api/app/main.py`, `apps/api/app/ai_gateway/residency.py`, `docs/agent-tasks.md`.

Not yet verified: running CI status, Cloud Build trigger state, live Cloud Run revisions, browser E2E results, production OAuth behavior, actual Cloud SQL region, and test counts.

Agent: ChatGPT GPT-6 — repository static audit.

## Follow-up static inspection — OAuth and deployment manifests (2026-10-25)

- **Residency discrepancy is not resolved:** `infra/cloudrun/api.yaml` refers to Cloud SQL instance `tood-os:europe-west2:tood-db`, while the README names `tood-os-instance` in `us-east4`. The README may be stale. **Verify the live database attachment and actual Cloud SQL region before asserting a residency violation.**
- **Three API targets appear in code/config:** `cloudbuild.yaml` specifies an older-looking `a.run.app` URL; `infra/cloudrun/web.yaml` uses `https://api.tood.uk`; README documents a different `a.run.app` URL. Confirm the live URL, DNS and actual environment.
- **Deployment mechanism differs:** `scripts/deploy.sh` uses mutable `:latest` images and `gcloud run services replace` with manifests; `cloudbuild.yaml` deploys commit-tagged images with `gcloud run deploy`. This strengthens the need to inspect active triggers and pick one controlled release path.
- **OAuth review:** `apps/api/app/routes_oauth.py` returns a raw session token as JSON to a Next.js callback route. The full browser callback and cookie implementation must be inspected before concluding the token handling is safe. The Google account lookup falls back to linking an existing local user by email; verify `email_verified` handling and account-linking policy before release. No exploit is claimed from this static review alone.
- **Signup:** `apps/api/app/core/config.py` defaults `allow_signup=True`, but `infra/cloudrun/api.yaml` explicitly sets `ALLOW_SIGNUP=false`. Confirm live environment and intended onboarding.

These are additional source findings; no test execution or production inspection has occurred.
