"""Rule-based requirement extraction with deterministic verification (blueprint section 14).

The extractor proposes; code verifies. A language-model extractor can replace `extract_candidates`
behind the same output shape, and every candidate still passes `verify_verbatim`.
"""

import difflib
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


def verify_verbatim(text: str, source_text: str, threshold: float = 0.9) -> bool:
    """The requirement wording must be found in its source block (blueprint V2)."""
    if not text or not source_text:
        return False
    if text in source_text:
        return True
    matcher = difflib.SequenceMatcher(None, text.lower(), source_text.lower(), autojunk=False)
    match = matcher.find_longest_match(0, len(text), 0, len(source_text))
    return match.size / max(len(text), 1) >= threshold


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
        for sentence in SENTENCE_SPLIT.split(block["text"]):
            sentence = sentence.strip()
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
