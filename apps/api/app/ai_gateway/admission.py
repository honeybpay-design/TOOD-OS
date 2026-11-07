"""Fail-closed signed model admission. No client, credential or network access."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
import pathlib
import re
import stat
from dataclasses import dataclass

from app.ai_gateway.errors import AIProviderUnavailable

SCHEMA = "tood-model-admission-v1"
SDK_VERSION = "2.33.0"
MAX_BYTES = 65536
MAX_VALIDITY_SECONDS = 7 * 86400
CLOUD_MODELS = frozenset({"gemini-4-argon", "gemini-3.5-flash"})
THRESHOLDS = {
    "requirement_recall_pass_fail": 0.98,
    "requirement_recall_all": 0.95,
    "requirement_precision": 0.9,
    "deadline_accuracy": 1.0,
    "source_span_accuracy": 0.98,
    "citations_to_nonexistent_evidence": 0,
    "word_limit_compliance": 1.0,
    "draft_quality_mean_min": 3.5,
    "analysis_seconds_p90_max": 300,
    "honesty_when_insufficient": 0.95,
    "scope_compliance": 0.98,
    "consistency_overlap": 0.95,
    "schema_validity": 0.995,
}
MAX_METRICS = {"citations_to_nonexistent_evidence", "analysis_seconds_p90_max"}
APP = pathlib.Path(__file__).resolve().parents[1]
FIELDS = frozenset(
    {
        "status",
        "provider",
        "api",
        "project",
        "region",
        "model_id",
        "model_versions",
        "sdk_version",
        "prompt_version",
        "source_digest",
        "prompt_digest",
        "parser_digest",
        "rules_digest",
        "thresholds_digest",
        "evaluation_digest",
        "dataset_digest",
        "metrics",
        "approval_ref",
        "not_before",
        "expires_at",
    }
)


class ModelNotAdmitted(AIProviderUnavailable):
    """No remote execution is authorized by the current admission artifact."""


def deny():
    raise ModelNotAdmitted("AI model is not admitted") from None


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def source_digest(paths):
    digest = hashlib.sha256()
    for name in sorted(paths):
        path = APP / name
        if path.is_symlink() or not path.is_file():
            deny()
        data = path.read_bytes()
        key = name.encode("utf-8")
        digest.update(len(key).to_bytes(4, "big") + key + len(data).to_bytes(8, "big") + data)
    return digest.hexdigest()


def current_bindings():
    files = [p.relative_to(APP).as_posix() for p in APP.rglob("*.py") if "__pycache__" not in p.parts]
    return {
        "source_digest": source_digest(files),
        "prompt_digest": source_digest(["ai_gateway/gemini_provider.py", "ai_gateway/agent.py"]),
        "parser_digest": source_digest(["services/parsing.py", "services/requirements.py"]),
        "rules_digest": source_digest(["services/drafting.py", "services/requirements.py"]),
        "thresholds_digest": hashlib.sha256(canonical(THRESHOLDS)).hexdigest(),
    }


def utc_now():
    return dt.datetime.now(dt.UTC)


def sdk_version():
    return importlib.metadata.version("google-genai")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            deny()
        result[key] = value
    return result


def read_document(filename):
    path = pathlib.Path(filename)
    if not path.is_absolute() or not path.name.endswith(".admission.json"):
        deny()
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink() or before.st_size > MAX_BYTES:
        deny()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        actual = os.fstat(stream.fileno())
        if not stat.S_ISREG(actual.st_mode) or (before.st_dev, before.st_ino) != (actual.st_dev, actual.st_ino):
            deny()
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        deny()
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=lambda value: deny())


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        deny()
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.UTC)


def check_metrics(metrics):
    if not isinstance(metrics, dict) or set(metrics) != set(THRESHOLDS):
        deny()
    for key, threshold in THRESHOLDS.items():
        value = metrics[key]
        if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
            deny()
        if key == "citations_to_nonexistent_evidence" and type(value) is not int:
            deny()
        if key not in MAX_METRICS and value > (5 if key == "draft_quality_mean_min" else 1):
            deny()
        if value > threshold if key in MAX_METRICS else value < threshold:
            deny()


@dataclass(frozen=True)
class Admission:
    digest: str
    model_id: str
    model_versions: tuple[str, ...]
    prompt_version: str
    project: str
    region: str


def require_admission(config, prompt_version: str) -> Admission:
    """Validate fresh signed evidence before any SDK construction or model call."""
    try:
        filename = config.ai_admission_file
        public_key = config.ai_admission_public_key
        key_id = config.ai_admission_key_id
        model_id = config.ai_model_id
        if not all(isinstance(v, str) and v for v in [filename, public_key, key_id, model_id]):
            deny()
        if config.gcp_project != "tood-os" or config.gcp_region != "europe-west2" or model_id not in CLOUD_MODELS:
            deny()
        if sdk_version() != SDK_VERSION:
            deny()
        envelope = read_document(filename)
        if not isinstance(envelope, dict) or set(envelope) != {"schema", "key_id", "payload", "signature"}:
            deny()
        if envelope["schema"] != SCHEMA or envelope["key_id"] != key_id:
            deny()
        payload = envelope["payload"]
        if not isinstance(payload, dict) or set(payload) != FIELDS:
            deny()
        signature = base64.b64decode(envelope["signature"], validate=True)
        key_bytes = base64.b64decode(public_key, validate=True)
        if len(signature) != 64 or len(key_bytes) != 32:
            deny()
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        signed = {k: envelope[k] for k in ("schema", "key_id", "payload")}
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature, canonical(signed))
        expected = {
            "status": "admitted",
            "provider": "google-cloud",
            "api": "generateContent-v1",
            "project": "tood-os",
            "region": "europe-west2",
            "model_id": model_id,
            "sdk_version": SDK_VERSION,
            "prompt_version": prompt_version,
            **current_bindings(),
        }
        if any(payload[key] != value for key, value in expected.items()):
            deny()
        versions = payload["model_versions"]
        if not isinstance(versions, list) or not 1 <= len(versions) <= 8:
            deny()
        if any(not isinstance(v, str) or not re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", v) for v in versions) or len(
            set(versions)
        ) != len(versions):
            deny()
        for key in ["evaluation_digest", "dataset_digest"]:
            if (
                not isinstance(payload[key], str)
                or not re.fullmatch(r"[0-9a-f]{64}", payload[key])
                or payload[key] == "0" * 64
            ):
                deny()
        if not isinstance(payload["approval_ref"], str) or not 1 <= len(payload["approval_ref"]) <= 256:
            deny()
        start, end, now = timestamp(payload["not_before"]), timestamp(payload["expires_at"]), utc_now()
        if not 0 < (end - start).total_seconds() <= MAX_VALIDITY_SECONDS or not start <= now < end:
            deny()
        check_metrics(payload["metrics"])
        return Admission(
            hashlib.sha256(canonical(envelope)).hexdigest(),
            model_id,
            tuple(versions),
            prompt_version,
            "tood-os",
            "europe-west2",
        )
    except ModelNotAdmitted:
        raise
    except Exception:
        deny()
