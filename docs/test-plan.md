# Development team test plan (run before any use)

| ID | Area | How to run | Pass criteria | Blueprint |
|---|---|---|---|---|
| D01 | Installation | `python scripts/verify_install.py` | 17/17 checks pass | 24, 30 |
| D02 | Migrations | Run `python scripts/migrate.py` twice | Second run skips every file | 21 |
| D03 | Tenant isolation | `pytest tests/test_tenant_isolation.py` | 6 pass | 19, 22 |
| D04 | Default deny | No tenant context returns zero rows | `test_no_context_returns_zero_rows` passes | 19 |
| D05 | Cross-tenant write | Insert with another organisation's ID | Rejected by RLS | 22 |
| D06 | Append-only | `pytest tests/test_append_only.py` | App role cannot update or delete; trigger blocks the admin role | 18 |
| D07 | Hash chain | `pytest tests/test_provenance_hash.py` | Tampering and removal detected at the right revision | 18 |
| D08 | Residency guard | `pytest tests/test_residency_guard.py` | Non UK/EU regions rejected | 12 |
| D09 | Role privileges | `app_user` and `auth_user` | Not superuser, no BYPASSRLS | 19 |
| D10 | CI | Open a pull request | All jobs green | 25 |
| D11 | Secrets | Gitleaks job in CI | No findings | 25 |
| D12 | Web build | `cd apps/web && npm run build` | Succeeds | 7 |
| D13 | API contract | `python scripts/export_openapi.py` | Client generated and web still builds | 20 |
| D14 | Evaluation gates | `python scripts/check_gates.py` | Fails with no results; passes only when every threshold is met | 28 |
| D15 | Clean machine | Fresh clone on Windows and on macOS or Linux, run bootstrap | Passes on both | 30 |
| D16 | Rollback | `docker compose down -v`, then bootstrap again | Passes | 27 |
| D17 | End-to-end workflow | `pytest tests/test_workflow.py` | 15 pass: upload, extraction, evidence, draft, claims, approval, gated export, tampering detected | 13, 14, 17, 18 |
| D18 | Access control | `pytest tests/test_api_security.py` | 11 pass: other organisations see and change nothing, roles enforced, no credentials refused | 19, 22 |
| D19 | Web page | Run the API, open http://localhost:8000, follow README "Run it" with the sample files | Every step works; the export opens in Word; flags block export until acknowledged | 7 |

Sign-off: tester ____________  date ________  result ________
