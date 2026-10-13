# Verification Note — Review Findings Fix

**Date:** iteration 2 (after gemini-integration-review.json)
**Findings addressed:** 3 (2 blocking, 1 non-blocking)

---

## Finding 1 — verify_claim fail-open parsing (blocking) ✅ FIXED

**Problem:** `"SUPPORTED" in answer` was too loose — any hedged prose or quota-error text containing
the substring "SUPPORTED" would pass the check.

**Fix applied:** Changed to `answer.strip() == "SUPPORTED"` (exact match after stripping whitespace).
The logic now requires the model to reply with exactly `SUPPORTED` and nothing else. Any hedged,
prefaced, or unexpected response evaluates as `False`.

File changed: `apps/api/app/ai_gateway/agent.py`

---

## Finding 2 — verify_claim TemplateProvider bypass (blocking) ✅ FIXED

**Problem:** When `AI_PROVIDER=template`, `TemplateProvider.draft()` returns drafting prose, not a
binary classification reply. Whether "SUPPORTED" happened to appear in the output was accidental,
making verification arbitrary.

**Fix applied:** Added an `is_local` guard at the top of `verify_claim()`. When the provider returns
`is_local=True` (i.e., TemplateProvider), the method immediately returns `False` for any factual
claim, signalling that verification is inconclusive rather than silently passing it.

This is a safe behaviour change: callers that relied on `verify_claim` returning `True` with the
template provider for factual claims were already relying on undefined/accidental behaviour. `False`
is the correct fail-safe: the claim is not verified, so it should not be treated as verified.

File changed: `apps/api/app/ai_gateway/agent.py`

---

## Finding 3 — admit_model.py missing negative verify_claim check (non-blocking) ✅ FIXED

**Problem:** The six admission checks did not exercise `verify_claim()` against a hallucinated
figure, leaving a gap where a model could pass admission but still mis-verify at runtime.

**Fix applied:** Added Check 7 to `scripts/admit_model.py`:
- Feeds `verify_claim()` a claim with fabricated figures (999 projects, 75% saving) against evidence
  that states the real figures (42 projects, 18% saving).
- For local/template providers: asserts the result is `False` (correct fail-safe).
- For remote providers (Gemini): asserts the model actively returns `False`.

File changed: `scripts/admit_model.py`

---

## Test results

```
44 passed, 3 warnings in 66.73s
```

Ruff lint: `All checks passed!`

---

## Behaviour-visible changes

`ToodAgent.verify_claim()` now returns `False` for factual claims when `AI_PROVIDER=template`.
Previously the result was arbitrary (depended on whether drafting prose happened to contain
"SUPPORTED"). The new behaviour is deterministic and correct: the template provider cannot classify,
so the method signals that verification is inconclusive.

No routes, no API responses, no export gate, and no test assertions were changed.
