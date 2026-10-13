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
None
