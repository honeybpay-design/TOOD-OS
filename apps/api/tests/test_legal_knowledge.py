"""Safety regression checks for the UK legal knowledge source gate."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from app.services.legal_knowledge import (
    LegalEvidenceError,
    LegalSource,
    retrieve_legal_evidence,
    validate_source_url,
)


def source(**overrides):
    base = LegalSource(
        source_id="pa2023-s1",
        title="Procurement Act 2023",
        url="https://www.legislation.gov.uk/ukpga/2023/54/contents",
        text="Section 1\n\nThis section concerns procurement objectives.",
        retrieved_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        effective_from=date(2025, 2, 24),
    )
    return replace(base, **overrides)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.legislation.gov.uk/ukpga/2023/54",
        "https://legislation.gov.uk.evil.example/ukpga/2023/54",
        "https://evil.example/ukpga/2023/54",
        "https://user@www.gov.uk/path",
        "https://www.gov.uk:8443/path",
    ],
)
def test_rejects_untrusted_sources(url):
    with pytest.raises(LegalEvidenceError):
        validate_source_url(url)


def test_never_returns_unapproved_source():
    assert retrieve_legal_evidence("procurement objectives", [source()], on_date=date(2026, 11, 8)) == []


def test_rejects_modified_approved_source():
    original = source()
    tampered = replace(original, approved=True, approved_digest=original.digest, text="Altered objectives")
    assert retrieve_legal_evidence("objectives", [tampered], on_date=date(2026, 11, 8)) == []


def test_dates_must_be_explicit_and_applicable():
    original = source()
    missing_date = replace(original, approved=True, approved_digest=original.digest, effective_from=None)
    assert retrieve_legal_evidence("objectives", [missing_date], on_date=date(2026, 11, 8)) == []
    approved = replace(original, approved=True, approved_digest=original.digest)
    assert retrieve_legal_evidence("objectives", [approved], on_date=date(2025, 2, 23)) == []
    assert len(retrieve_legal_evidence("objectives", [approved], on_date=date(2026, 11, 8))) == 1


def test_citation_includes_official_url_and_digest():
    original = source()
    approved = replace(original, approved=True, approved_digest=original.digest)
    citations = retrieve_legal_evidence("procurement objectives", [approved], on_date=date(2026, 11, 8))
    assert citations
    assert citations[0].source_sha256 == approved.digest
    assert citations[0].source_url == approved.url
    assert citations[0].effective_from == "2025-02-24"


def test_invalid_effective_date_range_fails_closed():
    with pytest.raises(LegalEvidenceError):
        source(effective_from=date(2026, 1, 1), effective_until=date(2025, 1, 1))
