"""Pinned real google-genai SDK, explicitly invalid synthetic fixture credentials, fake HTTP only."""

import importlib.metadata
import json
import socket
from types import SimpleNamespace

import google.auth
import httpx
import pytest
from admission_fixtures import MODEL, VERSION, write_policy
from app.ai_gateway import admission, gemini_provider
from app.ai_gateway.errors import AIProviderUnavailable
from google import genai
from google.auth.credentials import Credentials


class SyntheticCredentials(Credentials):
    """Public dummy token for MockTransport only; never valid with Google."""

    def __init__(self):
        super().__init__()
        self.token = "SYNTHETIC-INVALID-FOR-REAL-API"

    def refresh(self, request):
        raise AssertionError("Real token refresh forbidden in offline SDK tests")


@pytest.fixture
def cloud_contract(monkeypatch, tmp_path):
    assert importlib.metadata.version("google-genai") == "2.33.0"
    synthetic = write_policy(admission, tmp_path / "SYNTHETIC.admission.json")
    monkeypatch.setattr(gemini_provider, "settings", synthetic)

    def forbidden(*args, **kwargs):
        raise AssertionError("Real network or credential lookup forbidden")

    monkeypatch.setattr(google.auth, "default", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_ENTERPRISE"):
        monkeypatch.delenv(key, raising=False)
    state = {"requests": [], "status": 200, "version": VERSION, "finish": "STOP", "text": "Synthetic SDK response."}

    def transport(request):
        state["requests"].append(request)
        body = {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": state["text"]}]},
                    "finishReason": state["finish"],
                    "safetyRatings": [],
                }
            ]
        }
        if state["version"] is not None:
            body["modelVersion"] = state["version"]
        if state["status"] != 200:
            body = {
                "error": {
                    "code": state["status"],
                    "message": "SYNTHETIC_DIAGNOSTIC_MUST_NOT_ESCAPE",
                    "status": "UNAVAILABLE",
                }
            }
        return httpx.Response(state["status"], json=body, request=request)

    real_client = genai.Client

    def factory(**kwargs):
        assert kwargs["enterprise"] is True
        assert kwargs["project"] == "tood-os" and kwargs["location"] == "europe-west2"
        options = kwargs["http_options"]
        assert options.api_version == "v1"
        assert options.base_url == "https://europe-west2-aiplatform.googleapis.com"
        assert options.timeout == 30000 and options.retry_options.attempts == 1
        assert options.client_args == {"trust_env": False}
        options.client_args = {"trust_env": False, "transport": httpx.MockTransport(transport)}
        return real_client(credentials=SyntheticCredentials(), **kwargs)

    monkeypatch.setattr(genai, "Client", factory)
    return SimpleNamespace(state=state, provider=gemini_provider.GeminiProvider(), settings=synthetic)


def test_real_pinned_sdk_uses_london_cloud_v1_and_actual_model_version(cloud_contract):
    result = cloud_contract.provider.generate("Synthetic SDK contract", [], 80)
    assert result.model_id == VERSION and result.requested_model_id == MODEL
    requests = cloud_contract.state["requests"]
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.headers["authorization"] == "Bearer SYNTHETIC-INVALID-FOR-REAL-API"
    assert request.url.host == "europe-west2-aiplatform.googleapis.com"
    assert (
        request.url.path
        == f"/v1/projects/tood-os/locations/europe-west2/publishers/google/models/{MODEL}:generateContent"
    )
    body = json.loads(request.content)
    assert body["generationConfig"]["maxOutputTokens"] == 2048
    assert body["generationConfig"]["responseMimeType"] == "text/plain"
    assert not body.get("tools") and not body.get("cachedContent")
    assert "Synthetic SDK contract" in body["contents"][0]["parts"][0]["text"]


@pytest.mark.parametrize("version", [None, "UNADMITTED"])
def test_actual_sdk_missing_or_changed_model_version_denies(cloud_contract, version):
    cloud_contract.state["version"] = version
    with pytest.raises(AIProviderUnavailable):
        cloud_contract.provider.generate("Synthetic", [], 80)
    assert len(cloud_contract.state["requests"]) == 1


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "SAFETY"])
def test_actual_sdk_truncation_or_safety_stop_denies(cloud_contract, finish):
    cloud_contract.state["finish"] = finish
    with pytest.raises(AIProviderUnavailable):
        cloud_contract.provider.generate("Synthetic", [], 80)
    assert len(cloud_contract.state["requests"]) == 1


@pytest.mark.parametrize("status", [400, 429, 503])
def test_actual_sdk_error_has_no_retry_fallback_or_raw_diagnostic(cloud_contract, status):
    cloud_contract.state["status"] = status
    with pytest.raises(AIProviderUnavailable) as error:
        cloud_contract.provider.generate("Synthetic", [], 80)
    assert "SYNTHETIC_DIAGNOSTIC" not in str(error.value)
    assert len(cloud_contract.state["requests"]) == 1


def test_actual_sdk_empty_response_denies(cloud_contract):
    cloud_contract.state["text"] = ""
    with pytest.raises(AIProviderUnavailable):
        cloud_contract.provider.generate("Synthetic", [], 80)
    assert len(cloud_contract.state["requests"]) == 1


def test_revoked_policy_denies_before_actual_sdk_http_request(cloud_contract, tmp_path):
    write_policy(admission, tmp_path / "SYNTHETIC.admission.json", lambda e: e["payload"].update(status="revoked"))
    with pytest.raises(AIProviderUnavailable):
        cloud_contract.provider.generate("Synthetic", [], 80)
    assert cloud_contract.state["requests"] == []
