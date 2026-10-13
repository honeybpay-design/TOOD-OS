"""Draft text, provenance spans and claim verification (blueprint sections 17 and 18)."""

import difflib
import re

from app.ai_gateway.provider import Segment

EV_TAG = re.compile(r"\[EV:([0-9a-fA-F-]{36})\]")
CLAIM = re.compile(
    r"(\d|[£$€%])|\b(ISO|Cyber Essentials|certified|accredited|clients?|customers?|delivered|years?|projects?|"
    r"contracts?|awarded|reduced|saved|increased)\b",
    re.I,
)
SENTENCE = re.compile(r".+?[.!?](?=\s|$)(?:\s*\[EV:[0-9a-fA-F-]{36}\])*|.+$", re.S)
NUMBER = re.compile(r"\d[\d,.]*")


def word_count(text: str) -> int:
    return len(re.sub(r"\[EV:[0-9a-fA-F-]{36}\]", "", text).split())


def segments_to_text(segments: list[Segment]) -> tuple[str, list[list]]:
    text, spans, pos = "", [], 0
    for i, seg in enumerate(segments):
        piece = (" " if i else "") + seg.text
        start = pos + (1 if i else 0)
        text += piece
        pos += len(piece)
        spans.append([start, pos, seg.origin])
    return text, spans


def origins_per_char(text: str, spans: list[list]) -> list[str]:
    chars = ["human"] * len(text)
    for start, end, origin in spans:
        for i in range(start, min(end, len(text))):
            chars[i] = origin
    return chars


def compress(chars: list[str]) -> list[list]:
    spans: list[list] = []
    for i, origin in enumerate(chars):
        if spans and spans[-1][2] == origin and spans[-1][1] == i:
            spans[-1][1] = i + 1
        else:
            spans.append([i, i + 1, origin])
    return spans


def respan(old_text: str, old_spans: list[list], new_text: str) -> list[list]:
    """Characters kept from the old text keep their origin. Anything typed or pasted becomes 'human'."""
    old = origins_per_char(old_text, old_spans)
    new = ["human"] * len(new_text)
    matcher = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            new[j1:j2] = old[i1:i2]
    return compress(new)


def ai_retained_ratio(spans: list[list]) -> float:
    total = sum(e - s for s, e, _ in spans)
    return round(sum(e - s for s, e, o in spans if o == "ai") / total, 4) if total else 0.0


def split_sentences(text: str) -> list[str]:
    """A sentence ends at . ! or ? followed by space, and keeps its [EV:id] tags that follow the full stop."""
    found = SENTENCE.findall(text.strip())
    return [x.strip() for x in found if x.strip()]


def verify_claims(text: str, evidence_by_id: dict[str, dict]) -> list[dict]:
    """Every sentence that states a fact needs a valid, approved evidence tag that supports it."""
    results = []
    for sentence in split_sentences(text):
        if not CLAIM.search(EV_TAG.sub("", sentence)):
            continue
        ids = [m.lower() for m in EV_TAG.findall(sentence)]
        status, reason = "supported", "ok"
        if not ids:
            status, reason = "unsupported", "no evidence cited"
        else:
            bare = EV_TAG.sub("", sentence)
            for ev_id in ids:
                ev = evidence_by_id.get(ev_id)
                if ev is None:
                    status, reason = "unsupported", f"evidence {ev_id[:8]} does not exist in this organisation"
                    break
                if ev["status"] != "approved":
                    status, reason = "unsupported", f"evidence '{ev['title']}' is not approved"
                    break
                missing = [n for n in NUMBER.findall(bare) if n not in ev["body"]]
                if missing:
                    status, reason = "unsupported", f"figure {missing[0]} is not in the cited evidence"
                    break
        results.append({"sentence_span": sentence, "evidence_ids": ids, "status": status, "reason": reason})
    return results
