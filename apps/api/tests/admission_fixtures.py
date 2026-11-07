"""Public deterministic TEST ONLY admission fixtures; never runtime trust or live eval."""

import base64
import datetime as dt
import hashlib
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

MODEL = "gemini-3.5-flash"
VERSION = MODEL + "-SYNTHETIC-001"
PROMPT = "gemini-draft-1"


def write_policy(admission, path, mutate=None, *, now=None):
    # Public, predictable bytes expressly unsuitable for production. No random key generation.
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    now = now or dt.datetime.now(dt.UTC)
    payload = {
        "status": "admitted",
        "provider": "google-cloud",
        "api": "generateContent-v1",
        "project": "tood-os",
        "region": "europe-west2",
        "model_id": MODEL,
        "model_versions": [VERSION],
        "sdk_version": "2.33.0",
        "prompt_version": PROMPT,
        **admission.current_bindings(),
        "evaluation_digest": hashlib.sha256(b"SYNTHETIC TEST ONLY EVALUATION").hexdigest(),
        "dataset_digest": hashlib.sha256(b"SYNTHETIC TEST ONLY DATASET").hexdigest(),
        "metrics": dict(admission.THRESHOLDS),
        "approval_ref": "SYNTHETIC-TEST-ONLY",
        "not_before": (now - dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    envelope = {"schema": admission.SCHEMA, "key_id": "TEST-ONLY", "payload": payload}
    if mutate:
        mutate(envelope)
    envelope["signature"] = base64.b64encode(private.sign(admission.canonical(envelope))).decode("ascii")
    path.write_bytes(admission.canonical(envelope))
    return SimpleNamespace(
        ai_provider="gemini",
        gcp_project="tood-os",
        gcp_region="europe-west2",
        allowed_regions={"europe-west2"},
        ai_model_id=MODEL,
        ai_admission_file=str(path.resolve()),
        ai_admission_key_id="TEST-ONLY",
        ai_admission_public_key=base64.b64encode(public).decode("ascii"),
    )


def response(text="Synthetic primary output.", version=VERSION, finish="STOP"):
    return SimpleNamespace(
        text=text,
        model_version=version,
        candidates=[
            SimpleNamespace(
                finish_reason=finish,
                safety_ratings=[],
                content=SimpleNamespace(parts=[SimpleNamespace(text=text)]),
            )
        ],
    )
