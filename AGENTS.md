# Instructions for AI coding agents

Read this file completely before changing anything. The authoritative specification is the
**TOOD-OS Full Master Blueprint v1.1**. Section numbers below refer to it.

## What you may do
- Work on a branch and open a pull request. Never push to `main`.
- Run any local command in this repository: `docker compose`, `python scripts/*.py`, `pytest`, `ruff`, `npm`.
- Follow `docs/agent-tasks.md` in order. Record each task's result in `docs/install-report.md`.

## What you must never do
- Never use, request or invent production credentials. You work in local and staging only (section 25).
- Never call an AI provider from business code. Every model call goes through `app/ai_gateway` (section 12).
- Never weaken or remove: verbatim requirement checks, claim verification, export gate, provenance and
  hash chain, Model Admission Test, the append-only triggers, forced RLS, or the rule that no bid is
  submitted automatically (ADRs marked "must not be weakened", section 32).
- Never use a plain `SET` for tenant context. Use `tenant_connection()` (it uses `set_config(..., true)`).
- Never commit secrets, `.env`, customer data, tender documents or golden-set material.
- Never edit an applied migration. Add a new numbered file in `migrations/`.
- Never mark a task done without its acceptance check passing. If a check fails, stop and report; do not
  change the check to make it pass.

## Human review is required before merge for
Authentication, RLS and migrations, billing, the AI Gateway, data deletion, provenance and anchoring,
and anything under `security/`.

## Commit and PR rules
- Commit message ends with a trailer: `Agent: <tool name and version>`.
- Every PR states: what changed, which section of the blueprint it implements, how it was tested, and
  which acceptance checks passed.
- A change to a prompt, model, parser or rule includes its evaluation result (section 28).

## Commands
| Purpose | Command |
|---|---|
| Start local stack | `docker compose up -d --wait` |
| Apply migrations | `python scripts/migrate.py` |
| Verify installation | `python scripts/verify_install.py` (must end `17/17 checks passed`) |
| Run API tests | `cd apps/api && pytest -q` |
| Run API | `cd apps/api && uvicorn app.main:app --reload --port 8000` |
| Lint | `cd apps/api && ruff check .` |
| Check evaluation gates | `python scripts/check_gates.py` |

## Layout
`apps/api` FastAPI modular monolith · `apps/web` Next.js · `packages/ui` design system ·
`packages/api-client` generated client · `workers` job handlers · `prompts` versioned prompts ·
`rules` versioned compliance rules · `evals` golden set and thresholds · `migrations` SQL ·
`infra/terraform` infrastructure · `docs/adr` decisions · `runbooks` · `security` threat model.
## Additional Engineering and Production Standards

### Architecture and Code Quality
- Inspect the existing architecture before proposing modifications.
- Preserve all mandatory security and compliance controls.
- Identify root causes and avoid temporary workarounds.
- Prefer maintainable, modular and testable implementations.
- Document architectural decisions and significant changes.

### Premium UI/UX Standards
- Follow the existing design system and component architecture.
- Ensure responsive layouts across desktop, tablet and mobile.
- Target WCAG 2.2 AA accessibility.
- Implement clear navigation, consistent typography and appropriate interaction feedback.
- Verify loading, empty, error and success states.
- Do not use fabricated testimonials, customer numbers, certifications or performance claims.

### Production Readiness
- Verify application health checks, structured logging and error handling.
- Review performance, database queries and resource consumption.
- Check authentication, authorization and tenant isolation.
- Validate configuration and secret-management practices.
- Prepare staging verification and rollback procedures.
- Never deploy to production without explicit human approval.

### Agent Continuity
- Read docs/agent-tasks.md before starting work.
- Record completed tasks and actual test results in docs/install-report.md.
- Maintain a clear record of blockers, unresolved issues and next actions.
- Never claim completion without passing the required acceptance checks.
- If a mandatory check fails, stop the affected workflow and report the failure.

### Security and Compliance
- Preserve all existing mandatory security controls and architectural decisions.
- Review dependencies for known vulnerabilities.
- Do not bypass security checks to make tests pass.
- Require human review for security-sensitive changes.
- Never expose secrets or sensitive customer information.

### Release and Go-to-Market Readiness
- Verify core user journeys and onboarding workflows.
- Review operational documentation and support procedures.
- Identify launch blockers and distinguish them from optional improvements.
- Require evidence-based verification before declaring production readiness.

### Priority and Conflict Resolution
- The TOOD-OS Full Master Blueprint v1.1 remains authoritative.
- Existing non-negotiable security and compliance rules take precedence.
- These additional standards supplement, but never override, the existing instructions.
- Escalate conflicts or ambiguous requirements for human review.
