# Verification Note — Gemini Integration

**Date:** 2025-07-17  
**Step:** Iteration 1 (no prior review file found)

## Files Changed / Created

| Action  | Path |
|---------|------|
| Modified | `apps/api/pyproject.toml` — added 4 GCP dependencies |
| Modified | `apps/api/app/core/config.py` — added `gcp_project`, `gcp_region` fields |
| Modified | `.env` — appended `AI_PROVIDER=template`, `GCP_PROJECT=tood-os`, `GCP_REGION=europe-west2` |
| Created  | `apps/api/app/ai_gateway/gemini_provider.py` |
| Modified | `apps/api/app/ai_gateway/provider.py` — added `gemini` case to `get_provider()` |
| Created  | `apps/api/app/ai_gateway/agent.py` |
| Created  | `apps/api/app/core/monitoring.py` |
| Modified | `apps/api/app/main.py` — added request latency middleware, startup health ping |
| Created  | `scripts/admit_model.py` |

## Test Results

```
10 passed, 3 warnings in 15.95s
```

Tests run: `test_health.py`, `test_residency_guard.py`, `test_provenance_hash.py`

The remaining 4 test files (`test_api_security.py`, `test_append_only.py`, `test_tenant_isolation.py`,
`test_workflow.py`) all require a live PostgreSQL connection and skip/timeout without one — this was
pre-existing behaviour unrelated to this change.

## Lint Results

```
ruff check . → All checks passed!
```

## Test Compatibility Decision

`google-cloud-aiplatform` is installed in the venv (v2.4.0). Per the implementation spec's
"IMPORTANT TEST COMPATIBILITY" section, **Option A** was applied:

- `AI_PROVIDER=template` in `.env` (not `gemini`) so tests using `conftest.py`'s `setdefault` logic
  continue to get the `TemplateProvider`.
- `ai_provider: str = "template"` kept as the Python default in `config.py`.
- Production environments must set `AI_PROVIDER=gemini` via their own env configuration.

`GeminiProvider` falls back to `TemplateProvider` when vertexai SDK is unavailable (Option B is also
coded in as a belt-and-suspenders safety net for environments where the SDK is absent).

`CloudMonitor` uses lazy client initialisation — the GCP `MetricServiceClient` is not created at
import time, only on first metric write, so startup never blocks in environments without GCP credentials.
