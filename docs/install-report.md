# Install report

| Task | Result (PASS/FAIL) | Evidence (output or link) | Date | Agent and version |
|---|---|---|---|---|
| T00 Prerequisites | PASS | git 2.55.0 / Python 3.12.10 / Docker 29.6.2 / Compose v5.3.1 | 2026-10-13 | wf-coder |
| T01 Bootstrap | PASS | 17/17 checks passed | 2026-10-13 | wf-coder |
| T02 Test suite | PASS | 44 passed, 0 failed, 0 skipped | 2026-10-13 | wf-coder |
| T03 Run the API | PASS | /healthz → {"status":"ok"}, /readyz → {"status":"ready"}, demo.py → export 200, data/demo_submission.docx exists (37546 bytes) | 2026-10-13 | wf-coder |
| T04 Clean rebuild | PASS | 17/17 checks passed, 4 migrations skipped (already applied), 44 passed 0 failed | 2026-10-13 | wf-coder |
| T05 Web application | PASS | Next.js 16.4.0, npm run build succeeded | 2026-10-13 | wf-coder |
| T06 API client | PASS | openapi.json and schema.d.ts exist, web build OK | 2026-10-13 | wf-coder |
| T07 Continuous integration | N/A | CI config exists at .github/workflows/ci.yml, requires GitHub push to verify | 2026-10-13 | wf-coder |

Installed versions (Python, Node, Docker, Next.js, key packages):
- Python: 3.12.10
- Node: v22.23.1
- Docker: 29.6.2
- Next.js: 16.4.0
- FastAPI: 0.143.0
- PostgreSQL: 16 (pgvector/pgvector:pg16)

Open issues:
- 2026-10-22: launch audit reports NO_GO: Firebase Hosting session cookie mismatch; full readiness remains unverified.

## Gemini launch audit extension — 2026-10-22

- Branch: `codex/gemini-launch-audit`; implements advisory tooling for blueprint sections 12, 25 and 28.
- Offline regression evaluation: 4 tests passed (`python -m unittest discover -s scripts -p test_launch_audit.py -v`).
- Local audit executed: exit 1 / NO_GO. `hosting_session_cookie` FAIL; remaining checks UNVERIFIED. No failed check was changed to pass.
- Live Gemini 4 regional availability, staging credentials, model quality, full installation/API/web/evaluation acceptance: NOT VERIFIED.
- No production credentials, live model call, automatic fixes, deployment, merge or admission performed.
- Instructions and limits: `docs/gemini-launch-audit.md`. Agent: Codex (GPT-6).

## Pending changes and workflow verification — 2026-10-22

- T00 versions verified: Git 2.55.0, Python 3.12.10, Node 22.23.1, Docker 29.6.2, Compose 5.3.1. Docker config access warning in sandbox.
- Installation verification against explicit localhost development database: FAIL, connection timeout; output ended `2/3 checks passed`, not `17/17 checks passed`. Stopped the database-dependent acceptance sequence; API acceptance and full stack remain unverified.
- CI now supports manual `workflow_dispatch` and includes the offline launch audit tests. Production deployment remains restricted to pushes to main with existing environment protections.
- `workers/` contains only `.gitkeep`: no worker executable or worker workflow exists to run. CI is the only workflow currently present.
- Pending source/docs/skill assets are being prepared for a branch push. Generated caches, desktop metadata, temporary screenshots/reports, absent staged UI-v01 files, and tender sample files are excluded from this commit without deleting local files.
- Full Ruff check: FAIL, 5 existing import-order errors in `test_api_security.py`, `test_append_only.py`, `test_health.py`, `test_residency_guard.py`, `test_tenant_isolation.py`. Existing acceptance checks were not altered. New launch audit files had import ordering normalized before this full check.
- Full API suite and web build were not run after the installation acceptance failure. Any PR is draft/unverified, not release-ready.
