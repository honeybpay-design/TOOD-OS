"""ToodAgent: orchestrates AI tasks through the AI Gateway. Never imports vendor SDKs directly."""

from __future__ import annotations

import re
from typing import Any

from app.ai_gateway.provider import Segment, get_provider

EV_TAG = re.compile(r"\[EV:([0-9a-fA-F-]{36})\]")
CLAIM = re.compile(
    r"(\d|[£$€%])|\b(ISO|Cyber Essentials|certified|accredited|clients?|customers?|delivered|years?|projects?|"
    r"contracts?|awarded|reduced|saved|increased)\b",
    re.I,
)


class ToodAgent:
    """Orchestrates AI tasks: extraction, drafting, verification, monitoring."""

    def extract_requirements(self, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Use Gemini to analyse blocks and extract requirements with verbatim check."""
        provider = get_provider()
        evidence_items = [
            {"id": str(i), "body": block.get("text", "")} for i, block in enumerate(blocks) if block.get("text")
        ]
        prompt = (
            "Analyse the following tender document blocks and extract all requirements. "
            "For each requirement, provide: id (integer), text (verbatim from the block), "
            "type (mandatory/desirable/informational), and block_id reference. "
            "Return one requirement per line as: REQ|<id>|<type>|<text>|<block_id>"
        )
        segments = provider.draft(prompt, evidence_items, word_limit=None)
        full_text = " ".join(s.text for s in segments)
        requirements = []
        for line in full_text.splitlines():
            parts = line.split("|")
            if len(parts) == 5 and parts[0] == "REQ":
                requirements.append(
                    {
                        "id": parts[1].strip(),
                        "type": parts[2].strip(),
                        "text": parts[3].strip(),
                        "block_id": parts[4].strip(),
                    }
                )
        return requirements

    def draft_answer(self, prompt: str, evidence: list[dict[str, Any]], word_limit: int) -> list[Segment]:
        """Create a draft answer with evidence citations."""
        provider = get_provider()
        return provider.draft(prompt, evidence, word_limit)

    def verify_claim(self, claim: str, evidence_body: str) -> bool:
        """Verify a claim is supported by the provided evidence body.

        Returns True only when the AI model explicitly replies "SUPPORTED".
        Returns False when the provider is local/template (cannot classify),
        when the model replies "NOT SUPPORTED", or when the reply is ambiguous.
        Non-factual claims (no numbers, certifications, etc.) bypass AI and return True.
        """
        if not CLAIM.search(EV_TAG.sub("", claim)):
            return True  # non-factual claim: no verification needed
        provider = get_provider()
        # Local/template providers cannot perform binary classification; they always
        # return drafting prose, never a clean SUPPORTED/NOT SUPPORTED verdict.
        # Return False so the caller knows verification was inconclusive rather than
        # silently passing an unverifiable claim.
        if getattr(provider, "is_local", False):
            return False
        # Sanitise inputs to prevent prompt injection: strip control characters,
        # collapse newlines to spaces, and truncate to safe lengths.
        sanitised_claim = claim.strip().replace("\r", "").replace("\n", " ")[:1000]
        sanitised_evidence = evidence_body.strip().replace("\r", "").replace("\n", " ")[:4000]
        verification_prompt = (
            "You are a claim verifier. Reply with exactly one word: SUPPORTED or NOT_SUPPORTED.\n\n"
            f"<CLAIM>{sanitised_claim}</CLAIM>\n"
            f"<EVIDENCE>{sanitised_evidence}</EVIDENCE>"
        )
        evidence_items = [{"id": "ev-verify", "body": evidence_body}]
        segments = provider.draft(verification_prompt, evidence_items, word_limit=10)
        # Require an exact "SUPPORTED" reply (after stripping whitespace) to avoid
        # fail-open on hedged prose, quota errors, or any text that merely contains
        # "SUPPORTED" as a substring (e.g. "NOT SUPPORTED" or "I believe SUPPORTED").
        answer = " ".join(s.text for s in segments).strip().upper()
        return answer == "SUPPORTED"

    def health_check(self) -> dict[str, Any]:
        """Check AI system health: latency, quota, region compliance."""
        provider = get_provider()
        if hasattr(provider, "health_check"):
            return provider.health_check()
        return {"status": "ok", "model_id": provider.model_id, "region": provider.region, "is_local": provider.is_local}
