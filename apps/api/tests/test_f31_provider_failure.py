"""F31-A real API/PG failure atomicity on the guarded synthetic test target."""

import uuid

import pytest
from admission_fixtures import MODEL, write_policy
from admission_fixtures import response as synthetic_response
from app.ai_gateway import admission, gemini_provider
from app.ai_gateway.gemini_provider import GeminiProvider
from conftest import SAMPLES


@pytest.mark.parametrize(
    "scenario",
    [
        "primary_error",
        "missing_sdk",
        "malformed_response",
        "wrong_version",
        "missing_version",
        "truncated",
        "safety",
        "revoked_in_flight",
    ],
)
def test_failed_generation_returns_503_without_success_rows_and_recovers(
    client, accounts, admin, monkeypatch, tmp_path, scenario
):
    account = accounts("F31 synthetic organization")
    headers = account["headers"]
    response = client.post("/v1/tenders", headers=headers, json={"title": "F31 synthetic tender"})
    assert response.status_code == 201
    tender = response.json()
    response = client.post(
        f"/v1/tenders/{tender['id']}/documents",
        headers=headers,
        files={"file": ("synthetic.txt", (SAMPLES / "sample_tender.txt").read_bytes(), "text/plain")},
    )
    assert response.status_code == 201
    questions = client.get(f"/v1/tenders/{tender['id']}/questions", headers=headers)
    assert questions.status_code == 200 and questions.json()
    question_id = questions.json()[0]["id"]
    org_id = uuid.UUID(account["org_id"])

    def counts():
        return tuple(
            admin.execute(query, (org_id,)).fetchone()[0]
            for query in (
                "SELECT count(*) FROM drafts WHERE org_id=%s",
                "SELECT count(*) FROM revisions WHERE org_id=%s",
                "SELECT count(*) FROM audit_events WHERE org_id=%s",
            )
        )

    before = counts()
    calls = []
    synthetic_settings = write_policy(admission, tmp_path / "SYNTHETIC.admission.json")

    class FakeClient:
        def __init__(self):
            self.models = self

        def generate_content(self, *, model, contents, config):
            calls.append(model)
            if scenario == "primary_error":
                raise RuntimeError("SYNTHETIC_DIAGNOSTIC_MUST_NOT_ESCAPE")
            if scenario == "revoked_in_flight":
                write_policy(
                    admission, tmp_path / "SYNTHETIC.admission.json", lambda e: e["payload"].update(status="revoked")
                )
            if scenario == "wrong_version":
                return synthetic_response(version="UNAPPROVED")
            if scenario == "missing_version":
                return synthetic_response(version=None)
            if scenario in {"truncated", "safety"}:
                return synthetic_response(finish="MAX_TOKENS" if scenario == "truncated" else "SAFETY")
            return synthetic_response(text=None if scenario == "malformed_response" else "Synthetic response.")

        def close(self):
            pass

    with monkeypatch.context() as patch:
        patch.setattr(gemini_provider, "settings", synthetic_settings)
        patch.setattr(gemini_provider, "_create_client", lambda *args: FakeClient())
        provider = GeminiProvider()
        provider._available = scenario != "missing_sdk"
        patch.setattr("app.routes.get_provider", lambda: provider)
        failed = client.post(f"/v1/questions/{question_id}/drafts", headers=headers)
    assert failed.status_code == 503
    assert failed.json() == {"detail": "AI generation is temporarily unavailable"}
    assert "SYNTHETIC_DIAGNOSTIC" not in failed.text
    assert calls == ([] if scenario == "missing_sdk" else [MODEL])
    assert counts() == before

    # The next clean request must work without retaining a failed transaction/version.
    recovered = client.post(f"/v1/questions/{question_id}/drafts", headers=headers)
    assert recovered.status_code == 201
    assert recovered.json()["model_id"] == "template-v0"
    assert recovered.json()["version"] == 1
    assert counts() == tuple(value + 1 for value in before)


def test_accepted_synthetic_generation_persists_actual_version_in_existing_snapshot(
    client, accounts, admin, monkeypatch, tmp_path
):
    from admission_fixtures import VERSION
    from app.core import audit

    account = accounts("F31-B synthetic accepted organization")
    headers = account["headers"]
    tender = client.post("/v1/tenders", headers=headers, json={"title": "F31-B synthetic tender"})
    assert tender.status_code == 201
    uploaded = client.post(
        f"/v1/tenders/{tender.json()['id']}/documents",
        headers=headers,
        files={"file": ("synthetic.txt", (SAMPLES / "sample_tender.txt").read_bytes(), "text/plain")},
    )
    assert uploaded.status_code == 201
    questions = client.get(f"/v1/tenders/{tender.json()['id']}/questions", headers=headers)
    assert questions.status_code == 200 and questions.json()

    class FakeClient:
        def __init__(self):
            self.models = self

        def generate_content(self, **kwargs):
            return synthetic_response()

        def close(self):
            pass

    synthetic_settings = write_policy(admission, tmp_path / "SYNTHETIC.admission.json")
    with monkeypatch.context() as patch:
        patch.setattr(gemini_provider, "settings", synthetic_settings)
        patch.setattr(gemini_provider, "_create_client", lambda *args: FakeClient())
        provider = GeminiProvider()
        patch.setattr("app.routes.get_provider", lambda: provider)
        result = client.post(f"/v1/questions/{questions.json()[0]['id']}/drafts", headers=headers)
    assert result.status_code == 201 and result.json()["model_id"] == VERSION
    assert provider.model_id == MODEL
    draft_id = uuid.UUID(result.json()["id"])
    content = admin.execute("SELECT content FROM drafts WHERE id=%s", (draft_id,)).fetchone()[0]
    snapshot = admin.execute(
        "SELECT content_snapshot FROM revisions WHERE draft_id=%s AND seq=1", (draft_id,)
    ).fetchone()[0]
    assert content["model_id"] == snapshot["model_id"] == VERSION
    assert content["prompt_version"] == snapshot["prompt_version"] == "gemini-draft-1"
    assert set(snapshot) == {"text", "spans", "model_id", "prompt_version"}
    assert audit.verify(admin, uuid.UUID(account["org_id"]))[0] is True
