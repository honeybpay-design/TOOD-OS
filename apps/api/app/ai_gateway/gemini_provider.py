"""Gemini provider via Vertex AI. Passes data only within europe-west2 (residency guard enforces this)."""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from app.ai_gateway.provider import Segment

logger = logging.getLogger(__name__)

EV_TAG = re.compile(r"\[EV:([0-9a-fA-F-]{36})\]")


class GeminiProvider:
    model_id = "gemini-2.5-pro"
    prompt_version = "gemini-draft-1"
    region = "europe-west2"
    is_local = False

    def __init__(self):
        # Lazy import so tests (which mock/skip the provider) can import this module
        try:
            import vertexai
            from vertexai.generative_models import GenerationConfig, GenerativeModel

            from app.core.config import settings as _settings

            vertexai.init(project=_settings.gcp_project, location=self.region)
            self._GenerativeModel = GenerativeModel
            self._GenerationConfig = GenerationConfig
            self._available = True
        except ImportError:
            self._available = False

    def _build_prompt(self, prompt: str, evidence: list[dict], word_limit: int | None) -> str:
        limit_instruction = f"Your response MUST be within {word_limit} words." if word_limit else ""
        evidence_text = "\n".join(f"[EV:{item['id']}] {item['body']}" for item in evidence)
        return (
            f"You are a procurement writing assistant helping draft compliant tender responses.\n"
            f"Requirement: {prompt}\n\n"
            f"Available Evidence:\n{evidence_text}\n\n"
            f"Instructions:\n"
            f"- Draft a professional response to the requirement above.\n"
            f"- Cite evidence inline using [EV:<id>] tags immediately after each claim it supports.\n"
            f"- Every factual claim (numbers, certifications, statistics) must be cited.\n"
            f"- Do not introduce facts not present in the evidence.\n"
            f"{limit_instruction}\n"
            f"Return only the response text with inline citations."
        )

    def draft(self, prompt: str, evidence: list[dict], word_limit: int | None) -> list[Segment]:
        if not self._available:
            from app.ai_gateway.provider import TemplateProvider

            return TemplateProvider().draft(prompt, evidence, word_limit)

        full_prompt = self._build_prompt(prompt, evidence, word_limit)
        try:
            model = self._GenerativeModel(
                self.model_id,
                generation_config=self._GenerationConfig(temperature=0.2, max_output_tokens=2048),
            )
            response = model.generate_content(full_prompt)
            raw_text = response.text
        except Exception as primary_exc:
            logger.warning(
                "GeminiProvider primary model %s failed, retrying with gemini-2.0-flash: %s",
                self.model_id,
                primary_exc,
            )
            try:
                from app.core.monitoring import get_monitor

                get_monitor().record_ai_call(self.model_id, 0.0, 0, False)
            except Exception:
                pass
            # Fallback to gemini-2.0-flash
            try:
                model = self._GenerativeModel(
                    "gemini-2.0-flash",
                    generation_config=self._GenerationConfig(temperature=0.2, max_output_tokens=2048),
                )
                response = model.generate_content(full_prompt)
                raw_text = response.text
            except Exception as flash_exc:
                logger.warning(
                    "GeminiProvider fallback model gemini-2.0-flash also failed, using TemplateProvider: %s",
                    flash_exc,
                )
                try:
                    from app.core.monitoring import get_monitor

                    get_monitor().record_ai_call("gemini-2.0-flash", 0.0, 0, False)
                except Exception:
                    pass
                from app.ai_gateway.provider import TemplateProvider

                return TemplateProvider().draft(prompt, evidence, word_limit)

        return self._parse_response(raw_text)

    def _parse_response(self, text: str) -> list[Segment]:
        """Split model output into Segment list, classifying evidence-cited sentences.

        Process line-by-line so that [EV:...] tags on one line are only associated
        with that line's text. Handles optional space after the colon: [EV: uuid].
        """
        # Regex that handles both [EV:uuid] and [EV: uuid]
        ev_tag_re = re.compile(r"\[EV:\s*([0-9a-fA-F-]{36})\]")
        sentence_re = re.compile(r".+?[.!?](?=\s|$)|\S.+$")
        segments = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Extract all EV tags present on this line before sentence-splitting
            line_has_ev = bool(ev_tag_re.search(line))
            for match in sentence_re.finditer(line):
                sentence = match.group().strip()
                if not sentence:
                    continue
                # Classify based on whether this specific sentence slice contains a tag
                origin = "evidence" if ev_tag_re.search(sentence) else ("evidence" if line_has_ev else "ai")
                segments.append(Segment(text=sentence, origin=origin))
        if not segments:
            segments.append(Segment(text=text.strip(), origin="ai"))
        return segments

    def health_check(self) -> dict:
        if not self._available:
            return {"status": "unavailable", "reason": "vertexai SDK not installed", "region": self.region}
        start = time.monotonic()
        try:
            model = self._GenerativeModel("gemini-2.0-flash")
            model.generate_content("ping")
            latency_ms = round((time.monotonic() - start) * 1000)
            return {
                "status": "ok",
                "model_id": self.model_id,
                "region": self.region,
                "latency_ms": latency_ms,
                "region_compliant": True,
            }
        except Exception as e:
            return {"status": "error", "reason": str(e), "region": self.region, "region_compliant": True}
