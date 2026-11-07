"""Google Cloud Gen AI adapter; admission before SDK access, no implicit fallback."""

from __future__ import annotations

import os
import re
import time

from app.ai_gateway.admission import ModelNotAdmitted, require_admission
from app.ai_gateway.errors import AIProviderUnavailable
from app.ai_gateway.provider import GenerationResult, Segment
from app.core.config import settings


def _create_client(project, region):
    # Explicit Cloud route: never inherit Developer API/global/proxy defaults.
    if any(key in os.environ for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY")):
        raise AIProviderUnavailable("AI generation is unavailable")
    from google import genai
    from google.genai import types

    return genai.Client(
        enterprise=True,
        project=project,
        location=region,
        http_options=types.HttpOptions(
            api_version="v1",
            base_url="https://europe-west2-aiplatform.googleapis.com",
            timeout=30000,
            retry_options=types.HttpRetryOptions(attempts=1),
            client_args={"trust_env": False},
        ),
    )


def _record_failure(model_id):
    try:
        from app.core.monitoring import get_monitor

        get_monitor().record_ai_call(model_id, 0.0, 0, False)
    except Exception:
        pass


class GeminiProvider:
    model_id = ""  # selected explicitly only after signed admission; no retired default
    prompt_version = "gemini-draft-1"
    region = "europe-west2"
    is_local = False

    def __init__(self):
        self._config = settings
        self.model_id = settings.ai_model_id
        self.project = settings.gcp_project
        self.region = settings.gcp_region
        self._validate()
        try:
            from google.genai import Client, types

            self._available = callable(Client) and hasattr(types, "GenerateContentConfig")
        except ImportError:
            self._available = False

    def _validate(self):
        receipt = require_admission(self._config, self.prompt_version)
        if (receipt.model_id, receipt.project, receipt.region) != (self.model_id, self.project, self.region):
            raise ModelNotAdmitted("AI model is not admitted")
        return receipt

    def validate_result(self, result: GenerationResult) -> None:
        receipt = self._validate()
        if (
            result.admission_digest != receipt.digest
            or result.requested_model_id != self.model_id
            or result.model_id not in receipt.model_versions
            or result.prompt_version != self.prompt_version
        ):
            raise ModelNotAdmitted("AI model is not admitted")

    def draft(self, prompt: str, evidence: list[dict], word_limit: int | None) -> list[Segment]:
        return list(self.generate(prompt, evidence, word_limit).segments)

    def generate(self, prompt: str, evidence: list[dict], word_limit: int | None) -> GenerationResult:
        receipt = self._validate()
        if not self._available:
            raise AIProviderUnavailable("AI generation is unavailable")
        client = None
        try:
            from google.genai import types

            client = _create_client(self.project, self.region)
            response = client.models.generate_content(
                model=self.model_id,
                contents=self._build_prompt(prompt, evidence, word_limit),
                config=types.GenerateContentConfig(
                    max_output_tokens=2048,
                    response_mime_type="text/plain",
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            candidates = response.candidates
            if not candidates or len(candidates) != 1:
                raise AIProviderUnavailable("AI generation is unavailable")
            candidate = candidates[0]
            finish = getattr(candidate.finish_reason, "value", candidate.finish_reason)
            if finish != "STOP" or any(
                getattr(rating, "blocked", False) for rating in (candidate.safety_ratings or [])
            ):
                raise AIProviderUnavailable("AI generation is unavailable")
            parts = candidate.content.parts if candidate.content else None
            if not parts or any(
                getattr(part, name, None) is not None
                for part in parts
                for name in ("function_call", "executable_code", "code_execution_result", "inline_data", "file_data")
            ):
                raise AIProviderUnavailable("AI generation is unavailable")
            raw_text = response.text
            if not isinstance(raw_text, str) or not raw_text.strip() or len(raw_text) > 80000:
                raise AIProviderUnavailable("AI generation is unavailable")
            version = response.model_version
            fresh = self._validate()
            if fresh.digest != receipt.digest or not isinstance(version, str) or version not in fresh.model_versions:
                raise ModelNotAdmitted("AI model is not admitted")
            result = GenerationResult(
                tuple(self._parse_response(raw_text)), self.model_id, version, self.prompt_version, fresh.digest
            )
            self.validate_result(result)
            return result
        except ModelNotAdmitted:
            raise
        except AIProviderUnavailable:
            _record_failure(self.model_id)
            raise
        except Exception:
            _record_failure(self.model_id)
            raise AIProviderUnavailable("AI generation is unavailable") from None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

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
            return {"status": "unavailable", "reason": "Google Gen AI SDK unavailable", "region": self.region}
        start = time.monotonic()
        try:
            result = self.generate("ping", [], 10)
            return {
                "status": "ok",
                "model_id": result.model_id,
                "requested_model_id": self.model_id,
                "region": self.region,
                "latency_ms": round((time.monotonic() - start) * 1000),
                "region_compliant": True,
            }
        except AIProviderUnavailable:
            return {"status": "error", "reason": "AI provider health request failed", "region": self.region}
