#!/usr/bin/env python
"""Model Admission Test — blueprint section 28.

Runs a series of checks against the configured AI provider before it is allowed in production.
Prints PASS or FAIL for each check. Exit code 0 = all passed, 1 = at least one failed.
"""

from __future__ import annotations
import os
import sys
import pathlib

# Ensure the API package is on sys.path
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

# Load .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.ai_gateway.provider import get_provider  # noqa: E402
from app.services.drafting import verify_claims, word_count  # noqa: E402

SAMPLE_TENDER_BLOCKS = [
    {
        "id": "3f4e5a6b-0000-0000-0000-000000000001",
        "body": "We have delivered 42 successful procurement projects over 5 years, achieving an average cost saving of 18% for our clients.",
    },
    {
        "id": "3f4e5a6b-0000-0000-0000-000000000002",
        "body": "Our team holds ISO 9001 certification and Cyber Essentials Plus accreditation, renewed annually since 2019.",
    },
]
SAMPLE_PROMPT = "Describe your experience delivering procurement projects and your quality certifications."
WORD_LIMIT = 80

passed = []
failed = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))
        passed.append(name)
    else:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        failed.append(name)


print("=" * 60)
print("Model Admission Test — TOOD-OS")
print("=" * 60)

provider = get_provider()

# Check 1: Region
check(
    "region=europe-west2",
    provider.region == "europe-west2" or getattr(provider, "is_local", False),
    f"region={provider.region!r}",
)

# Check 2: Draft runs without error
try:
    segments = provider.draft(SAMPLE_PROMPT, SAMPLE_TENDER_BLOCKS, WORD_LIMIT)
    draft_ok = len(segments) > 0
except Exception as e:
    segments = []
    draft_ok = False
    print(f"  ERROR drafting: {e}")
check("draft_produces_output", draft_ok, f"{len(segments)} segments")

if segments:
    full_text = " ".join(s.text for s in segments)

    # Check 3: Word limit respected
    wc = word_count(full_text)
    check("word_limit_respected", wc <= WORD_LIMIT * 1.15, f"{wc} words (limit {WORD_LIMIT})")

    # Check 4: Evidence citation present
    import re
    ev_tags = re.findall(r"\[EV:[0-9a-fA-F-]{36}\]", full_text)
    check("evidence_citation_present", len(ev_tags) > 0, f"{len(ev_tags)} citation(s) found")

    # Check 5: Verbatim requirement check (verify_claims) still functional
    evidence_by_id = {item["id"]: {"body": item["body"], "status": "approved", "title": "Sample"} for item in SAMPLE_TENDER_BLOCKS}
    try:
        claims = verify_claims(full_text, evidence_by_id)
        # verify_claims runs without exception = function is intact
        check("verbatim_check_functional", True, f"{len(claims)} claim(s) checked")
    except Exception as e:
        claims = []
        check("verbatim_check_functional", False, str(e))

    # Check 6: No unsupported claims with figures from outside evidence
    unsupported = [c for c in (claims if segments else []) if c["status"] == "unsupported"]
    check("no_hallucinated_figures", len(unsupported) == 0, f"{len(unsupported)} unsupported claim(s)")

print("=" * 60)
print(f"Result: {len(passed)} passed, {len(failed)} failed")
if failed:
    print("FAILED checks:", ", ".join(failed))
    print("OVERALL: FAIL")
    sys.exit(1)
else:
    print("OVERALL: PASS")
    sys.exit(0)
