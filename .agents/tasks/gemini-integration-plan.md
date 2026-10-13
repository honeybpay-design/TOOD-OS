# Implementation Plan — Gemini + Agent Layer + Cloud Monitoring

**Task:** Integrate Vertex AI Gemini 2.5 Pro, a ToodAgent orchestration layer, and Google Cloud
Monitoring/Logging into the TOOD-OS FastAPI backend without breaking any of the 44 existing tests.

**Key invariants (must not be weakened at any step):**
- Verbatim requirement checks (`verify_verbatim` in `services/requirements.py`)
- Claim verification (`verify_claims` in `services/drafting.py`)
- Export gate (`_readiness` check in `routes.py`)
- Append-only triggers and hash chain (existing `audit_events`, `revisions` tables)
- Forced RLS (`tenant_connection()` — never use plain `SET`)
- All AI calls through `app/ai_gateway` only — no vendor SDK imports in business code

---

## Step-by-step plan

- [ ] 1. **Add GCP and monitoring dependencies to `pyproject.toml`**

  Append `google-cloud-aiplatform>=1.60`, `google-auth>=2.30`, `google-cloud-monitoring>=2.20`, and
  `google-cloud-logging>=3.10` to the `dependencies` list. These are optional at runtime (code handles
  `ImportError` gracefully), but listing them here means `pip install -e .` installs them when the
  package is installed in a GCP-connected environment.

  Decision: pin lower bounds only (>=), not exact versions, consistent with every other dependency in
  `pyproject.toml`.

  Files: `apps/api/pyproject.toml`

  Verify:
  ```
  cd apps/api && python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['dependencies'])"
  ```
  Expected: the output list contains all four new package strings. (No test run needed — this is a pure
  manifest change; the test suite does not install from the manifest in CI.)

---

- [ ] 2. **Add GCP settings to `config.py` and update `.env`**

  In `apps/api/app/core/config.py`, add two new fields to `Settings`:
  - `gcp_project: str = "tood-os"`
  - `gcp_region: str = "europe-west2"`

  Keep `ai_provider: str = "template"` **unchanged** in the Python default so that tests that do
  not set the environment variable continue to get `template`.

  In `.env`, add three lines:
  ```
  AI_PROVIDER=gemini
  GCP_PROJECT=tood-os
  GCP_REGION=europe-west2
  ```
  Also add `europe-west2` to `AI_ALLOWED_REGIONS` in `.env` so `check_endpoint()` accepts it:
  ```
  AI_ALLOWED_REGIONS=uk-south,eu-west-2,eu-west-1,eu-central-1,europe-west2,europe-west1,europe-west4
  ```

  Why not change the Python default to `'gemini'`? `conftest.py` calls `os.environ.setdefault` for
  every key found in `.env`, so if `AI_PROVIDER` is already set (as it will be once `.env` is loaded),
  `setdefault` won't overwrite it — but the test environment does **not** set `AI_PROVIDER` explicitly,
  so it would inherit `gemini` from `.env` and fail when the GCP SDK is absent. Keeping the Python
  default as `'template'` is a safer backstop. If the env var is unset, the tests still get the
  template provider.

  Files: `apps/api/app/core/config.py`, `.env`

  Verify:
  ```
  cd apps/api && python -c "
  import os; os.environ['AI_PROVIDER']='template'
  from app.core.config import Settings
  s = Settings()
  assert s.ai_provider == 'template'
  assert s.gcp_project == 'tood-os'
  assert s.gcp_region == 'europe-west2'
  assert 'europe-west2' in s.allowed_regions
  print('config OK')
  "
  ```

---

- [ ] 3. **Create `GeminiProvider` in `apps/api/app/ai_gateway/gemini_provider.py`**

  Implement `GeminiProvider` to satisfy the same interface as `TemplateProvider`:

  ```python
  class GeminiProvider:
      model_id = "gemini-2.5-pro"
      prompt_version = "gemini-draft-1"
      region = "europe-west2"
      is_local = False

      def draft(self, prompt: str, evidence: list[dict], word_limit: int | None) -> list[Segment]:
          ...

      def health_check(self) -> dict:
          ...
  ```

  Implementation details:
  - Guard the entire `vertexai` import inside a `try/except ImportError` at module level; set a
    module-level flag `_VERTEXAI_AVAILABLE = False` when not installed.
  - `__init__` calls `vertexai.init(project=settings.gcp_project, location=self.region)` only when
    `_VERTEXAI_AVAILABLE` is `True`; otherwise raises `RuntimeError("google-cloud-aiplatform is not
    installed")`.
  - `draft()` logic:
    1. Build a system instruction: "You are a tender bid writer. Cite every factual claim with
       [EV:<uuid>] immediately after the sentence. Stay within the word limit."
    2. Assemble the user message: include `prompt`, the word limit, and each evidence item formatted as
       `[EV:<id>] <body>`.
    3. Call `GenerativeModel("gemini-2.5-pro").generate_content(...)` inside a try/except; on any
       exception, retry once with `"gemini-2.0-flash"` as the fallback model.
    4. Parse the response text into `list[Segment]`: split by sentence (reuse `SENTENCE` regex from
       `provider.py`); classify each sentence as `origin='evidence'` if it contains `[EV:...]` else
       `origin='ai'`.
    5. If `word_limit` is set, trim tail segments (never trim the first) until `word_count <= word_limit`,
       matching the same trim loop logic as `TemplateProvider.draft()`.
  - `health_check()` calls `draft("health ping", [], 20)` with a timer and returns
    `{"model": self.model_id, "region": self.region, "latency_ms": ..., "region_ok": True}`.
  - No vendor SDK import anywhere else in the codebase; only this file imports `vertexai`.

  Files: `apps/api/app/ai_gateway/gemini_provider.py`

  Verify:
  ```
  cd apps/api && python -c "
  import os; os.environ.setdefault('AI_PROVIDER','template')
  # Import must succeed even without vertexai installed
  from app.ai_gateway.gemini_provider import GeminiProvider, _VERTEXAI_AVAILABLE
  print('import OK, vertexai available:', _VERTEXAI_AVAILABLE)
  "
  ```
  Then run the full test suite to confirm no import-time side-effects broke anything:
  ```
  cd apps/api && pytest -q
  ```
  Expected: same pass count as before (44).

---

- [ ] 4. **Register `'gemini'` in `get_provider()` in `apps/api/app/ai_gateway/provider.py`**

  Add an `elif settings.ai_provider == "gemini":` branch that:
  1. Imports `GeminiProvider` from `app.ai_gateway.gemini_provider` (local import to keep the module
     importable even when vertexai is absent).
  2. Instantiates it, runs `check_provider(provider)` (which calls `check_endpoint('europe-west2')` —
     already in `allowed_regions`), and returns it.

  The `RuntimeError` for unknown providers remains as the final else clause.

  Decision: lazy local import (inside `get_provider()`) rather than top-level import, so that
  `provider.py` can be imported in test environments where `google-cloud-aiplatform` is not installed
  and `AI_PROVIDER=template`.

  Files: `apps/api/app/ai_gateway/provider.py`

  Verify:
  ```
  cd apps/api && python -c "
  import os; os.environ['AI_PROVIDER']='template'
  from app.ai_gateway.provider import get_provider
  p = get_provider()
  assert p.model_id == 'template-v0'
  print('template provider OK')
  "
  cd apps/api && pytest -q
  ```
  Expected: all 44 tests still pass.

---

- [ ] 5. **Create `ToodAgent` in `apps/api/app/ai_gateway/agent.py`**

  `ToodAgent` is an orchestration wrapper that sits between business code and the raw provider. All
  methods call `get_provider()` internally — they never import `vertexai` or any vendor SDK directly.

  ```python
  class ToodAgent:
      def extract_requirements(self, blocks: list[dict]) -> list[dict]:
          """Delegates to rule-based extractor; hooks provider for AI-enhanced classification
          if ai_provider != 'template'. Returns the same shape as extract_candidates()."""

      def draft_answer(
          self, prompt: str, evidence: list[dict], word_limit: int | None
      ) -> list[Segment]:
          """Calls provider.draft(); enforces word limit at agent level as a second gate."""

      def verify_claim(self, claim: str, evidence_body: str) -> bool:
          """True if the claim text is substantially present in evidence_body (uses verify_verbatim
          with threshold 0.7 — same threshold used elsewhere in requirements.py)."""

      def health_check(self) -> dict:
          """Returns {"provider": provider.model_id, "region": ..., "is_local": ...}; calls
          provider.health_check() when the method exists."""
  ```

  `extract_requirements` must always call `requirements.extract_candidates(blocks)` and then filter
  through `requirements.verify_verbatim(c["text_verbatim"], c["block_text"])` — the AI provider may
  assist classification but **never** bypasses the verbatim check.

  `draft_answer` respects word limits: after calling `provider.draft()`, if the result still exceeds
  `word_limit`, apply the same trim loop from `TemplateProvider` as a safety net.

  `verify_claim` is a thin convenience wrapper around `requirements.verify_verbatim`; it does not call
  the AI provider because the verbatim check is deterministic by design (blueprint section 14).

  Files: `apps/api/app/ai_gateway/agent.py`

  Verify:
  ```
  cd apps/api && python -c "
  import os; os.environ.setdefault('AI_PROVIDER','template')
  from app.ai_gateway.agent import ToodAgent
  agent = ToodAgent()
  segs = agent.draft_answer('Test prompt', [], 50)
  assert isinstance(segs, list)
  ok = agent.verify_claim('Tenderers must provide insurance.', 'Tenderers must provide insurance.')
  assert ok is True
  hc = agent.health_check()
  assert 'provider' in hc
  print('ToodAgent OK')
  "
  cd apps/api && pytest -q
  ```

---

- [ ] 6. **Create `CloudMonitor` in `apps/api/app/core/monitoring.py`**

  `CloudMonitor` records metrics to Google Cloud Monitoring and structured logs to Cloud Logging.
  Both clients are imported inside a `try/except ImportError` block; if either SDK is absent, all
  methods log a `WARNING` via Python's stdlib `logging` and return without raising.

  ```python
  class CloudMonitor:
      def record_ai_call(
          self, model_id: str, latency_ms: float, tokens_used: int, success: bool
      ) -> None: ...

      def record_api_request(
          self, endpoint: str, method: str, status_code: int, latency_ms: float
      ) -> None: ...

      def record_export(self, org_id: str, tender_id: str, success: bool) -> None: ...

      def health_ping(self) -> dict: ...
  ```

  Implementation decisions:
  - Use `google.cloud.monitoring_v3.MetricServiceClient` to write custom metrics under the prefix
    `custom.googleapis.com/tood_os/`.
  - Metric descriptors are written lazily (first call creates them if they do not exist, subsequent
    calls skip creation and catch `AlreadyExists`).
  - `record_ai_call` writes two metrics: `ai_call_latency_ms` (GAUGE, DOUBLE) and `ai_call_count`
    (CUMULATIVE, INT64) with label `model_id` and `success`.
  - `record_api_request` writes `api_request_latency_ms` with labels `endpoint` and `method`.
  - `record_export` writes `export_count` with label `success`.
  - `health_ping` returns `{"monitoring": "ok"}` when the SDK is available and credentials are valid,
    or `{"monitoring": "unavailable", "reason": "..."}` when not.
  - Instantiate a module-level singleton: `monitor = CloudMonitor()`.

  Files: `apps/api/app/core/monitoring.py`

  Verify:
  ```
  cd apps/api && python -c "
  import os; os.environ.setdefault('AI_PROVIDER','template')
  from app.core.monitoring import monitor
  # Should not raise even without GCP credentials
  monitor.record_ai_call('template-v0', 10.0, 0, True)
  monitor.record_api_request('/v1/me', 'GET', 200, 5.0)
  result = monitor.health_ping()
  assert 'monitoring' in result
  print('CloudMonitor OK:', result)
  "
  cd apps/api && pytest -q
  ```

---

- [ ] 7. **Add request latency middleware and startup health ping to `apps/api/app/main.py`**

  Add two things to `main.py`:

  **Middleware** — a `BaseHTTPMiddleware` subclass (from `starlette.middleware.base`) that:
  1. Records the start time before `await call_next(request)`.
  2. After the response, calls `monitor.record_api_request(request.url.path, request.method, response.status_code, latency_ms)`.
  3. Imports `monitor` from `app.core.monitoring` (local import at the top of the file).
  4. Swallows any exception from `monitor` (logs it; never lets a monitoring error surface to the client).

  **Startup event** — an `@app.on_event("startup")` (or `lifespan` context if preferred; `on_event`
  is simpler and consistent with the existing codebase which has no lifespan handler yet) that calls
  `monitor.health_ping()` and logs the result at `INFO` level.

  Files: `apps/api/app/main.py`

  Verify:
  ```
  cd apps/api && pytest tests/test_health.py -q
  cd apps/api && pytest -q
  ```
  Expected: `test_healthz` still passes; all 44 tests still pass. The middleware must not affect any
  existing test because `monitor.record_api_request` degrades gracefully when GCP is absent.

---

- [ ] 8. **Create model admission test script `scripts/admit_model.py`**

  A standalone Python script (no pytest, no FastAPI) that runs the Model Admission Test
  (blueprint section 28) against the configured AI provider:

  ```
  python scripts/admit_model.py
  ```

  Checks performed and expected output format:
  ```
  [PASS] draft returns list[Segment]
  [PASS] evidence citation [EV:<uuid>] present in at least one segment
  [PASS] word limit respected (requested 80, got N)
  [PASS] verbatim requirement check: requirement text found in source block
  [PASS] region == europe-west2
  [PASS] claim verification works (returns bool)
  [PASS] health_check returns latency and region
  Overall: 7/7 PASS
  ```

  The script:
  1. Imports `get_provider` from `app.ai_gateway.provider` and `ToodAgent` from
     `app.ai_gateway.agent`.
  2. Uses a hardcoded sample tender sentence ("The response must describe your approach to mobilisation.
     Maximum 80 words.") and two fake evidence items with real UUID keys.
  3. Calls `provider.draft(...)` directly for the Segment shape check.
  4. Calls `agent.draft_answer(...)` for the word-limit and citation checks.
  5. Calls `agent.verify_claim(...)` for the verbatim check.
  6. Calls `provider.health_check()` for the region check (only when the provider exposes it).
  7. Prints `[PASS]` or `[FAIL]` for each check and exits with code 0 (all pass) or 1 (any fail).
  8. Does **not** require a database connection.

  Files: `scripts/admit_model.py`

  Verify:
  ```
  cd apps/api && python ../../scripts/admit_model.py
  ```
  With `AI_PROVIDER=template` (the default): all checks that do not require a real model should pass;
  the region check for `template` prints `[SKIP] region check (local provider)` rather than `[FAIL]`.

---

## Summary of files created / modified

| Action | Path |
|--------|------|
| Modify | `apps/api/pyproject.toml` |
| Modify | `apps/api/app/core/config.py` |
| Modify | `.env` |
| **Create** | `apps/api/app/ai_gateway/gemini_provider.py` |
| Modify | `apps/api/app/ai_gateway/provider.py` |
| **Create** | `apps/api/app/ai_gateway/agent.py` |
| **Create** | `apps/api/app/core/monitoring.py` |
| Modify | `apps/api/app/main.py` |
| **Create** | `scripts/admit_model.py` |

## Dependency order

Items 1–2 are independent of each other and can be done in either order.
Items 3–4 depend on item 2 (need `settings.gcp_project`, `settings.gcp_region`).
Item 4 depends on item 3 (registers `GeminiProvider` in `get_provider()`).
Item 5 depends on item 4 (uses `get_provider()`).
Item 6 is independent (no dependency on items 3–5).
Item 7 depends on item 6 (imports `monitor`).
Item 8 depends on items 3–5 (calls provider and agent).

Recommended implementation order: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**.
After each item, run `cd apps/api && pytest -q` and confirm no regression before proceeding.

## Critical notes for the implementer

1. **Never import `vertexai` outside `gemini_provider.py`.** Any file in `services/`, `routes.py`,
   or elsewhere that needs AI must call `get_provider()` or use `ToodAgent`.

2. **The test environment does not have GCP credentials.** Every GCP SDK call must be inside a
   try/except that logs a warning and returns a degraded result. Tests must still pass with
   `AI_PROVIDER=template`.

3. **`conftest.py` uses `os.environ.setdefault`**, which means if `AI_PROVIDER` is set in the process
   environment *before* `conftest.py` runs (e.g., from a shell export), it will shadow the `.env`
   value. The Python default `"template"` is the final backstop but `.env` changes DO affect test
   runs if the env var isn't pre-set.

4. **Do not change `verify_verbatim`, `verify_claims`, `_readiness`, the hash chain, or the export
   gate.** These are immutable per AGENTS.md.

5. **No secrets in code.** GCP credentials are provided exclusively via Application Default
   Credentials (ADC): `gcloud auth application-default login` locally, Workload Identity on GKE.
   The `.env` file must not contain `GOOGLE_APPLICATION_CREDENTIALS` pointing to a key file.
