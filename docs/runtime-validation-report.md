# Runtime Validation Report

**Generated**: 2026-11-07  
**Target**: TOOD-OS repository workspace (local only)

## Summary

| Step | Status | Exit Code | Details |
|------|--------|-----------|---------|
| Startup | FAIL | 1 | API process started; `/readyz` returned 503 because PostgreSQL was unavailable. The local web app served pages. |
| Migrations/install | FAIL | 1 | Migration connection timed out; `verify_install.py` reported 2/3 checks. |
| API integration | FAIL | 1 | 19 passed, 1 failed, 31 skipped in 242.36s. DB-dependent coverage was skipped. |
| Browser E2E | FAIL | 1 | 2 passed, 1 failed. React hydration error #418 on the professional-plan login page. |
| Web build | FAIL | 1 | Initial build passed before dependency installation. The subsequent build stopped with Next.js `SecurityFatalError` for a known vulnerability. |
| Web lint | FAIL | 1 | 6 errors and 2 warnings. |
| API Ruff | PASS | 0 | All checks passed. |
| Evaluation gates | FAIL | 1 | `evals/results/latest.json` is missing. |

**Overall**: FAIL — required database-backed integration coverage is unavailable, the browser suite detects a hydration error, and web build/lint/evaluation gates fail.

## Environment and capability checks

- Python 3.12.10 was used; the checked-in `.venv` points to a missing interpreter, so the system Python 3.12 environment was used.
- Node.js v26.13.0, npm 11.20.0, Docker 29.9.2, Docker Compose v5.6.1.
- `npx playwright install --with-deps chromium` completed successfully; Chromium was available.
- Docker daemon responded to `docker info`, but the audit-owned PostgreSQL container remained `Created` after compose/start attempts. No embedded database fallback was used because tenant RLS, triggers, and migrations require PostgreSQL fidelity.
- API database URLs were overridden to `127.0.0.1`; no production endpoint or credentials were used.

## Evidence

### Startup and database

- `docker compose -p tood-e2e-audit up -d --wait` did not become ready.
- Retrying with the already available image still left the container in `Created`; `docker inspect` showed no started timestamp or state error, and localhost:5432 did not accept connections.
- `python scripts/migrate.py`: exit 1, `connection timeout expired`.
- `python scripts/verify_install.py`: exit 1, 2/3 checks passed; the database reachability check failed.
- The API process started. Its logs recorded `/healthz` as 200 and `/readyz` as 503 (`database unavailable`). Local HTTP probes exceeded the 8-second client timeout while the monitoring client also logged that local ADC credentials were absent.
- The test-owned container, network, and volume were removed with `docker compose -p tood-e2e-audit down -v --remove-orphans`; ports 3000, 8000, and 5432 were confirmed closed afterward.

### API tests

Command: `cd apps/api && python -m pytest -q`  
Exit code: **1** — **19 passed, 1 failed, 31 skipped**.

The failing test was `tests/test_api_security.py::test_requests_without_valid_credentials_are_refused`: its malformed-bearer case reached the auth database and could not connect. DB-dependent tests were skipped because the local database was unavailable. No claim is made for end-to-end RLS, workflow persistence, append-only enforcement, or hash-chain tamper coverage in this run.

### Browser E2E

Added [Playwright configuration](../apps/web/playwright.config.ts) and three runnable browser journeys:

- [public navigation](../apps/web/e2e/public-navigation.spec.ts) — home page CTA to login: PASS.
- [login plan context](../apps/web/e2e/login-plan.spec.ts) — plan notice and sign-in affordance rendered, but the page emitted React error **#418**: FAIL.
- [dashboard auth guard](../apps/web/e2e/dashboard-auth.spec.ts) — unauthenticated access returns to login with 401: PASS.

Command: `cd apps/web && npm run test:e2e -- --reporter=list`  
Exit code: **1** — **2 passed, 1 failed** in 53.5s.

The failing journey uses `plan=professional`; the plan value is read from `window.location.search` during render in [login/page.tsx](../apps/web/app/login/page.tsx), producing server/client markup mismatch. The authenticated workspace, write/read persistence, upload, drafting, approval, and export journeys could not be exercised without PostgreSQL.

### Build, lint, and gates

- The first `npm run build` completed successfully before Playwright was added.
- After installing the Playwright test dependency, the resolved Next.js version was 16.4.0. The next build compiled and completed TypeScript, then exited 1 with Next.js `SecurityFatalError`, identifying a known security vulnerability. The npm install audit summary reported 9 vulnerabilities (8 moderate, 1 critical). No security/dependency upgrade was attempted.
- `npm run lint`: exit 1, 6 errors and 2 warnings. Errors were in `apps/web/app/admin/page.tsx:53`, `apps/web/app/login/page.tsx:138,219,280`, and `apps/web/app/page.tsx:183,287`. Warnings were in `apps/web/app/layout.tsx:37` and `apps/web/app/page.tsx:1574`.
- `python scripts/check_gates.py`: exit 1 because `evals/results/latest.json` is missing.
- `python -m ruff check .` in `apps/api`: exit 0.

## Coverage gaps and disposition

- PostgreSQL-dependent tests and business journeys remain **UNVERIFIED**; the run is not a full-system E2E pass.
- No production code, migrations, secrets, customer data, or cloud resources were changed.
- The newly added browser suite is documented as D20 in [test-plan.md](test-plan.md). The web hydration error, Next.js security block, lint failures, and evaluation gate require separate remediation and rerun before sign-off.
