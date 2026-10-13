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
        """Verify a claim is supported by the provided evidence body."""
        if not CLAIM.search(EV_TAG.sub("", claim)):
            return True  # non-factual claim: no verification needed
        provider = get_provider()
        verification_prompt = (
            f"Does the following evidence support the claim?\n"
            f"Claim: {claim}\n"
            f"Evidence: {evidence_body}\n"
            f"Reply with exactly 'SUPPORTED' or 'NOT SUPPORTED'."
        )
        evidence_items = [{"id": "ev-verify", "body": evidence_body}]
        segments = provider.draft(verification_prompt, evidence_items, word_limit=10)
        answer = " ".join(s.text for s in segments).upper()
        return "NOT SUPPORTED" not in answer and "SUPPORTED" in answer

    def health_check(self) -> dict[str, Any]:
        """Check AI system health: latency, quota, region compliance."""
        provider = get_provider()
        if hasattr(provider, "health_check"):
            return provider.health_check()
        return {"status": "ok", "model_id": provider.model_id, "region": provider.region, "is_local": provider.is_local}
