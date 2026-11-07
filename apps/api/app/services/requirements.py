"""Rule-based requirement extraction with deterministic verification (blueprint section 14).

The extractor proposes; code verifies. A language-model extractor can replace `extract_candidates`
behind the same output shape, and every candidate still passes `verify_verbatim`.
"""

import hashlib
import re
from datetime import datetime
from zoneinfo import ZoneInfo

OBLIGATION = re.compile(
    r"\b(must not|must|shall not|shall|is required to|are required to|will be required|should|"
    r"is mandatory|are mandatory|mandatory)\b",
    re.I,
)
WORD_LIMIT = re.compile(
    r"(?:maximum of|max(?:imum)?\.?|up to|no more than|limit(?: of)?|not exceed(?:ing)?)?\s*"
    r"(\d{2,5})\s*words",
    re.I,
)
WEIGHT = re.compile(r"(\d{1,3})\s*%")
MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        start=1,
    )
}
DATE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", re.I)
TIME = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?\b|\bnoon\b|\bmidday\b", re.I)
DEADLINE_WORDS = re.compile(r"\b(deadline|closing|no later than|by|before|submitted by|received by)\b", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
LONDON = ZoneInfo("Europe/London")


VERBATIM_VERSION = "verbatim-source-units-v2"


def source_units(source_text: str) -> list[tuple[int, int]]:
    """Trusted sentence boundaries as Unicode code-point offsets into source.

    Segmentation depends only on stored parsed source, never candidate wording
    or candidate-supplied offsets. Only surrounding layout whitespace is outside
    a unit; no content is lowercased, normalized, fuzzy-matched or discarded.
    """
    ranges = []
    start = 0
    for separator in SENTENCE_SPLIT.finditer(source_text):
        ranges.append((start, separator.start()))
        start = separator.end()
    ranges.append((start, len(source_text)))
    units = []
    for start, end in ranges:
        while start < end and source_text[start].isspace():
            start += 1
        while end > start and source_text[end - 1].isspace():
            end -= 1
        if start < end:
            units.append((start, end))
    return units


def verify_verbatim(
    text: str, source_text: str, threshold: float = 0.9, *, expected_block_hash: str | None = None
) -> bool:
    """Require one exact complete trusted unit; threshold never relaxes equality.

    Keep the legacy threshold argument for caller compatibility only. Optional
    source-hash binding is mandatory at the ingestion boundary. Ambiguous repeat
    units fail closed rather than silently choosing an occurrence.
    """
    if not text or not source_text:
        return False
    if (
        expected_block_hash is not None
        and hashlib.sha256(source_text.encode("utf-8")).hexdigest() != expected_block_hash
    ):
        return False
    return sum(text == source_text[start:end] for start, end in source_units(source_text)) == 1


def parse_deadline(sentence: str) -> datetime | None:
    d = DATE.search(sentence)
    if not d or not DEADLINE_WORDS.search(sentence):
        return None
    day, month, year = int(d.group(1)), MONTHS[d.group(2).lower()], int(d.group(3))
    hour, minute = 12, 0  # a date with no time is treated as noon and flagged by low confidence upstream
    t = TIME.search(sentence)
    if t:
        if t.group(0).lower() in ("noon", "midday"):
            hour, minute = 12, 0
        else:
            hour, minute = int(t.group(1)), int(t.group(2))
            if t.group(3):
                hour = hour % 12 + (12 if t.group(3).lower() == "pm" else 0)
    try:
        return datetime(year, month, day, hour, minute, tzinfo=LONDON)
    except ValueError:
        return None


def classify(sentence: str) -> str:
    s = sentence.lower()
    if parse_deadline(sentence):
        return "deadline"
    if "pass/fail" in s or "pass or fail" in s or "will be rejected" in s or "disqualif" in s:
        return "pass_fail"
    if re.search(r"\b(declar|confirm that|self-certif)", s):
        return "declaration"
    if re.search(r"\b(attach|enclose|provide a copy|certificate|submit (?:a|the|your) (?:copy|policy|plan))", s):
        return "mandatory_document"
    if WORD_LIMIT.search(sentence) or re.search(r"\b(describe|explain|demonstrate|outline|set out|provide details)", s):
        return "scored_question"
    if re.search(r"\b(font|format|pdf|page limit|pages)\b", s):
        return "format_rule"
    return "information"


def extract_candidates(blocks: list[dict]) -> list[dict]:
    """blocks: parsed blocks with their database ids. Returns requirement candidates (not yet verified)."""
    out = []
    for block in blocks:
        for start, end in source_units(block["text"]):
            sentence = block["text"][start:end]
            if len(sentence) < 15:
                continue
            has_obligation = OBLIGATION.search(sentence)
            has_limit = WORD_LIMIT.search(sentence)
            outcome = re.search(r"pass/fail|will be rejected|will fail|disqualif", sentence, re.I)
            if not (has_obligation or has_limit or outcome or parse_deadline(sentence)):
                continue
            kind = classify(sentence)
            strong = bool(re.search(r"\b(must|shall|required|mandatory)\b", sentence, re.I))
            limit = WORD_LIMIT.search(sentence)
            weight = WEIGHT.search(block["text"])
            due = parse_deadline(sentence)
            confidence = 0.9 if (strong or due) else 0.7
            if kind == "deadline" and not TIME.search(sentence):
                confidence = 0.6  # a date without a time needs a human check
            out.append(
                {
                    "block_id": block["id"],
                    "unit_start": start,
                    "unit_end": end,
                    "verifier_version": VERBATIM_VERSION,
                    "block_text": block["text"],
                    "prompt": block["text"],
                    "text_verbatim": sentence,
                    "type": kind,
                    "title": (block.get("section_path") or sentence[:60]).split(" > ")[-1][:120],
                    "word_limit": int(limit.group(1)) if limit else None,
                    "weighting": float(weight.group(1)) if weight and kind == "scored_question" else None,
                    "due_at": due,
                    "confidence": confidence,
                }
            )
    return out
