"""AI Gateway providers. Business code calls get_provider(); it never imports a vendor SDK.

The local pack ships with the template provider only: it writes from approved evidence by quoting it,
so it can run with no model, no account and no data leaving the machine. It is a stand-in. A real model
provider implements `draft()` and must pass the Model Admission Test before it is enabled (blueprint section 28).
"""

import re
from dataclasses import dataclass

from app.ai_gateway.residency import check_provider
from app.core.config import settings

SENTENCE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Segment:
    text: str
    origin: str  # 'ai' | 'evidence'


class TemplateProvider:
    model_id = "template-v0"
    prompt_version = "template-draft-1"
    region = "local"
    is_local = True

    def draft(self, prompt: str, evidence: list[dict], word_limit: int | None) -> list[Segment]:
        segments = [Segment("This response addresses the requirement set out in the tender documents.", "ai")]
        for item in evidence[:3]:
            sentences = [s.strip() for s in SENTENCE.split(item["body"].strip()) if s.strip()][:2]
            for s in sentences:
                s = s if s[-1] in ".!?" else s + "."
                segments.append(Segment(f"{s} [EV:{item['id']}]", "evidence"))
        segments.append(Segment("Supporting evidence is cited against each statement above.", "ai"))
        if word_limit:
            while len(segments) > 2 and sum(len(s.text.split()) for s in segments) > word_limit:
                del segments[-2]  # drop the last evidence sentence, keep the closing line
        return segments


def get_provider():
    if settings.ai_provider == "template":
        provider = TemplateProvider()
        check_provider(provider)
        return provider
    if settings.ai_provider == "gemini":
        from app.ai_gateway.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        check_provider(provider)
        return provider
    raise RuntimeError(
        f"AI provider '{settings.ai_provider}' is not available. Connect and admit a model through the AI Gateway first."
    )
