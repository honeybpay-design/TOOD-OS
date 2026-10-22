# Gemini launch audit

Blueprint sections: 12 (Gateway), 25 (local/staging), 28 (evaluation).
Branch: `codex/gemini-launch-audit`. Human review required before merging Gateway changes.

## Run locally without credentials or API charges

```powershell
.venv/Scripts/python.exe scripts/launch_audit.py
```

Writes `tmp/launch-audit.json`. Exit 1 means NO_GO, including unverified checks.
This scans a fixed set of source files for the Firebase cookie mismatch; it does
not load `.env`, customer files, tender documents, or golden-set material.
The static cookie check identifies a configuration risk, not a completed OAuth test.

To run installation, API tests, web build and evaluation gates in order:

```powershell
.venv/Scripts/python.exe scripts/launch_audit.py --checks
```

Stops at the first failed command, timeout, skipped API test, or missing 17/17
installation confirmation. Raw subprocess output is not sent to Gemini or saved
in the report. Run the failing command directly for diagnostics. Login, billing,
restore, deployment and model admission still require independent verification;
this version cannot automatically produce a GO decision for the whole product.

## Optional paid Gemini 4 review

Use a dedicated staging project and staging-only Application Default Credentials.
Do not use production credentials. Existing API dependencies include google-auth
and httpx; no provider key is added to `.env`.

```powershell
$env:TOOD_AUDIT_ENV = 'staging'
.venv/Scripts/python.exe scripts/launch_audit.py --staging-project YOUR-STAGING-PROJECT-ID
```

The ADC project must match the specified project. The operator must ensure those
credentials are staging-only; the script cannot discover their complete IAM scope.
Only check IDs and PASS/FAIL/UNVERIFIED values leave the machine. The Gateway
makes one request to `gemini-4-argon` at `europe-west2`, with a 60-second HTTP
timeout and a 2048 output-token ceiling. ADC refresh is separate. This bounds
generation, not an exact monetary spend cap. No automatic retries, tools, edits,
deployments, global endpoint or model fallback are enabled.

Gemini API model existence has been verified in Google's model documentation.
Availability of this model on the regional Vertex endpoint, IAM access, quota,
and billing are NOT verified. A regional availability or credential error is
reported as ERROR, never as a template success. Credentials and upstream error
bodies are not written to the report.

Gemini provides advisory Thai actions; it cannot modify the deterministic release
decision. This integration does not admit Gemini 4 for tender drafting or replace
the existing production provider. Model Admission and existing evaluation gates
remain required for that separate change.

## Evaluation, 22 October 2026

`python -m unittest discover -s scripts -p test_launch_audit.py -v`: 4 passed.
Cases: fail/unknown cannot release; detect cookie mismatch without exposing .env;
reject non-staging before credential loading; reject arbitrary evidence IDs.
This is an offline boundary/regression evaluation, not a live model-quality eval.

Local audit: NO_GO (exit 1), hosting_session_cookie FAIL; other checks UNVERIFIED.
No paid model call, full stack acceptance check, deployment or merge performed.

Sources:
- https://ai.google.dev/gemini-api/docs/models
- https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference
- https://firebase.google.com/docs/hosting/manage-cache#using_cookies
