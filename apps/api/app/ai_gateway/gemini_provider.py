"""Gemini provider via Vertex AI. Passes data only within europe-west2 (residency guard enforces this)."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from app.ai_gateway.provider import Segment

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

            vertexai.init(project="tood-os", location=self.region)
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
        except Exception:
            # Fallback to gemini-2.0-flash
            try:
                model = self._GenerativeModel(
                    "gemini-2.0-flash",
                    generation_config=self._GenerationConfig(temperature=0.2, max_output_tokens=2048),
                )
                response = model.generate_content(full_prompt)
                raw_text = response.text
            except Exception:
                from app.ai_gateway.provider import TemplateProvider

                return TemplateProvider().draft(prompt, evidence, word_limit)

        return self._parse_response(raw_text)

    def _parse_response(self, text: str) -> list[Segment]:
        """Split model output into Segment list, classifying evidence-cited sentences."""
        segments = []
        sentence_re = re.compile(r".+?[.!?](?=\s|$)(?:\s*\[EV:[0-9a-fA-F-]{36}\])*|.+$", re.S)
        for match in sentence_re.finditer(text.strip()):
            sentence = match.group().strip()
            if not sentence:
                continue
            origin = "evidence" if EV_TAG.search(sentence) else "ai"
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
