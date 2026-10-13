"""Hash chain for append-only revisions (Blueprint section 18)."""

import hashlib
import json
from dataclasses import dataclass


def compute_hash(content: dict, metadata: dict, prev_hash: str | None) -> str:
    payload = json.dumps(
        {"content": content, "metadata": metadata, "prev": prev_hash or ""},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class Revision:
    content: dict
    metadata: dict
    prev_hash: str | None
    hash: str


def verify_chain(revisions: list[Revision]) -> tuple[bool, int | None]:
    """Return (ok, index_of_first_bad_revision)."""
    prev: str | None = None
    for i, r in enumerate(revisions):
        if r.prev_hash != prev or r.hash != compute_hash(r.content, r.metadata, prev):
            return False, i
        prev = r.hash
    return True, None


def ai_retained_ratio(spans: list[dict]) -> float:
    """spans: [{"origin": "ai"|"human"|..., "length": int}] for the approved version."""
    total = sum(s["length"] for s in spans)
    if total == 0:
        return 0.0
    return sum(s["length"] for s in spans if s["origin"] == "ai") / total
