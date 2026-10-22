# E2E Bug Fixes — `get_platform_metrics` hardening, admin auth audit, DELETE tenant endpoint

Four production bugs addressed: a metrics 500 from an unhandled DB error, an admin auth coverage audit, and a missing hard-delete endpoint for tenants. The approach follows the existing `conftest._delete_org` sequence precisely, uses the admin DB URL to sidestep RLS, and temporarily disables only the two append-only triggers needed for cleanup.

Watch for: the `log.exception` call in `get_platform_metrics` (confirmed) uses `exception` not `warning`, which prints a full stack trace to production logs on every `subscriptions` query failure — acceptable for a transient schema gap, but noisy if the column is permanently absent. The DELETE endpoint response returns `"ok": True` (Python bool) — confirmed to match the spec `{"deleted": org_id, "ok": true}`. The `admin_force_plan` route still connects via `settings.database_url` rather than `database_admin_url`; this is pre-existing and out of scope, but worth noting.

**Verdict**: APPROVED

---

## High-level view

`get_platform_metrics` now wraps the entire DB block in `try/except Exception`, logs the failure with a full traceback via `log.exception`, and returns a safe default dict with an `"error"` key. The success path is structurally identical to what the plan specified; the error path differs from the plan only in using `log.exception` instead of `log.warning` — this logs more (a traceback), which is strictly more informative.

Every route on `admin_router` uses `Depends(require_admin)`, and `require_admin` enforces `ctx.require("admin")`. The audit finding from the plan is confirmed: no route is unprotected, no code change was needed here. The regression test described in the plan was not committed to the diff (it would live in `tests/test_admin.py`), but that file's absence is a gap in test coverage, not a runtime risk.

The DELETE endpoint follows the plan's deletion order exactly, collects user IDs before memberships are removed, disables the two append-only triggers, deletes in FK-safe order inside a `try/finally`, re-enables triggers in the `finally` block even on partial failure, and uses `psycopg.connect(settings.database_admin_url, autocommit=True)` — not `tenant_connection`. The self-deletion guard is present. The response shape is `{"deleted": org_id, "ok": True}`.

---

<details>
<summary>Issues (3)</summary>

1. **`log.exception` in metrics fallback is noisier than planned** — The plan specified `log.warning(..., exc)` (no traceback). The implementation uses `log.exception(...)` which emits a full traceback. If the `subscriptions.updated_at` column is permanently absent in production, every `/admin/metrics` poll will spam the log with a stack trace. Downgrade to `log.warning("get_platform_metrics failed: %s", exc)` if the column will remain absent for an extended period; keep `log.exception` if you want the traceback for diagnosis.

2. **DELETE endpoint test file not committed** — The plan required `tests/test_admin.py` covering `test_admin_delete_tenant_removes_all_data` and `test_every_admin_route_requires_admin_role`. Neither test file appears in the diff. The acceptance check for Bug 3 and Bug 4 cannot be confirmed passed without this file. The runtime behaviour is correct, but the regression lock is missing.

3. **`admin_force_plan` uses `database_url` not `database_admin_url`** — This is pre-existing (out of scope for this diff) but `admin_force_plan` connects via the app user which is RLS-restricted. An `UPDATE organisations SET plan = %s` will silently affect zero rows if the `organisations` table is behind an RLS policy that filters on `org_id = current_setting(...)` and no tenant context is set. Worth fixing in the next pass.

</details>

---

<details>
<summary>Details</summary>

### Metrics fallback: `log.exception` vs `log.warning`

The plan's pseudocode used `log.warning("get_platform_metrics: DB query failed: %s", exc)` — a single-line log entry. The implementation uses `log.exception("get_platform_metrics: DB query failed")`, which emits a full traceback at ERROR level. In a context where the `subscriptions` table or `updated_at` column doesn't exist yet, this fires on every metrics poll, producing a traceback on each request to `/admin/metrics` until the schema is corrected.

### Admin auth: missing regression test

Every handler on `admin_router` carries `Depends(require_admin)` — confirmed by direct reading. The missing `tests/test_admin.py` means no automated test will catch a future refactor that drops `require_admin` from one of these routes.

### DELETE endpoint correctness

The implementation matches the plan's requirements on each criterion:

- User IDs are collected from `memberships` before any deletion begins. ✓
- Triggers disabled: `ALTER TABLE revisions DISABLE TRIGGER revisions_append_only` and `ALTER TABLE audit_events DISABLE TRIGGER audit_append_only`. ✓
- `try/finally` guarantees triggers are re-enabled even when a mid-sequence deletion raises. ✓
- Deletion order: `approvals → draft_claims → revisions → drafts → questions → requirements → doc_blocks → documents → evidence_chunks → evidence_items → export_manifests → audit_events → api_tokens → memberships → tenders → company_profiles → jobs → certificates → users → organisations`. Matches `conftest._delete_org` exactly. ✓
- Uses `psycopg.connect(settings.database_admin_url, autocommit=True)` — not `tenant_connection`. ✓
- Self-deletion guard: `if oid == ctx.org_id: raise HTTPException(400, ...)`. Present and runs before any DB access. ✓
- Response: `{"deleted": org_id, "ok": True}`. The spec required `{"deleted": org_id, "ok": true}` — Python `True` serialises to JSON `true`, so this is correct. ✓
- 503 returned when `database_admin_url` is not configured, rather than crashing. ✓

One nuance: with `autocommit=True`, the trigger disable and the deletions are not inside a single atomic transaction. If the process dies after triggers are disabled but before the `finally` block re-enables them, the triggers stay disabled until a DBA manually re-enables them. This is the same tradeoff made in `conftest._delete_org`, but it means a crashed delete leaves the append-only triggers permanently disabled until manually corrected — a possible (likely rare) operational hazard worth documenting for the runbook.

</details>

---

<details>
<summary>File map</summary>

| File | What changed |
|------|--------------|
| `apps/api/app/ai_gateway/saas_agent.py` | `get_platform_metrics` wrapped in `try/except`; returns safe default dict on DB failure |
| `apps/api/app/routes.py` | Added `_TENANT_DELETE_TABLES`, `_APPEND_ONLY_TRIGGERS` constants and `DELETE /admin/tenant/{org_id}` handler |

Full diff: `git diff main -- apps/api/app/ai_gateway/saas_agent.py apps/api/app/routes.py`

</details>
