"""Fail-closed, source-grounded UK procurement legal knowledge primitives.

This module deliberately does NOT call a model or mutate a database. The
existing ai_gateway owns every LLM call; only approved evidence may be sent
through it. Staging-only integration follows separate review and admission.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlparse

OFFICIAL_HOSTS = frozenset({
    "legislation.gov.uk",
    "www.legislation.gov.uk",
    "gov.uk",
    "www.gov.uk",
})

# Keep an allowlist instead of permitting every URL found in scraped content.
MAX_SOURCE_CHARS = 2_000_000
MAX_QUERY_CHARS = 1000
MAX_EXCERPT_CHARS = 2500
TOKEN = re.compile(r"[a-z0-9]+", re.I)


class LegalEvidenceError(ValueError):
    """Source evidence is absent, invalid, or not approved."""


def validate_source_url(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname.lower() not in OFFICIAL_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        raise LegalEvidenceError("An approved HTTPS UK government source is required")
    return url


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LegalSource:
    source_id: str
    title: str
    url: str
    text: str
    retrieved_at: datetime
    effective_from: date | None = None
    effective_until: date | None = None
    source_kind: str = "guidance"  # law, regulation, ppn, guidance
    approved: bool = False
    approved_digest: str | None = None

    def __post_init__(self) -> None:
        validate_source_url(self.url)
        if not self.source_id.strip() or not self.title.strip():
            raise LegalEvidenceError("Source identifier and title are required")
        if not self.text.strip() or len(self.text) > MAX_SOURCE_CHARS:
            raise LegalEvidenceError("Source text must be non-empty and within limits")
        if self.source_kind not in {"law", "regulation", "ppn", "guidance"}:
            raise LegalEvidenceError("Invalid legal source kind")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise LegalEvidenceError("Retrieval time must include timezone")
        if self.retrieved_at > datetime.now(timezone.utc):
            raise LegalEvidenceError("Retrieval time cannot be in the future")
        if self.effective_from and self.effective_until and self.effective_from > self.effective_until:
            raise LegalEvidenceError("Invalid effective-date range")

    @property
    def digest(self) -> str:
        return sha256_text(self.text)

    def eligible_on(self, on_date: date) -> bool:
        """A missing applicability date is NOT presumed current."""
        return (
            self.approved
            and self.approved_digest == self.digest
            and self.effective_from is not None
            and self.effective_from <= on_date
            and (self.effective_until is None or on_date <= self.effective_until)
        )


@dataclass(frozen=True)
class LegalCitation:
    source_id: str
    source_title: str
    source_url: str
    source_kind: str
    source_sha256: str
    retrieved_at: str
    effective_from: str
    excerpt: str


def retrieve_legal_evidence(
    question: str, sources: list[LegalSource], *, on_date: date, limit: int = 5
) -> list[LegalCitation]:
    """Lexical baseline for an approved corpus, not a substitute for legal review.

    If relevant verified evidence is absent the result is empty, never an
    ungrounded answer. Chronological applicability is caller-supplied.
    """
    if not question.strip() or len(question) > MAX_QUERY_CHARS:
        raise LegalEvidenceError("Question is empty or exceeds length limit")
    if not 1 <= limit <= 20:
        raise LegalEvidenceError("Invalid result limit")
    words = set(TOKEN.findall(question.casefold()))
    if not words:
        return []
    ranked: list[tuple[int, LegalCitation]] = []
    for source in sources:
        if not source.eligible_on(on_date):
            continue
        # Normalize without treating text as instructions; this is untrusted evidence.
        paragraphs = re.split(r"\n\s*\n", source.text)
        for paragraph in paragraphs:
            paragraph = " ".join(paragraph.split())
            matches = words.intersection(TOKEN.findall(paragraph.casefold()))
            if not matches:
                continue
            excerpt = paragraph[:MAX_EXCERPT_CHARS]
            citation = LegalCitation(
                source_id=source.source_id,
                source_title=source.title,
                source_url=source.url,
                source_kind=source.source_kind,
                source_sha256=source.digest,
                retrieved_at=source.retrieved_at.isoformat(),
                effective_from=source.effective_from.isoformat(),
                excerpt=excerpt,
            )
            ranked.append((len(matches), citation))
    ranked.sort(key=lambda item: (-item[0], item[1].source_id, item[1].excerpt))
    return [citation for _, citation in ranked[:limit]]
