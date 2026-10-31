"""Access control through the HTTP API: tenant isolation, roles, authentication, and unit checks on the safeguards."""

import json
import uuid

import pytest
from app.core.auth import add_member
from app.core.tenant import tenant_connection
from conftest import APP_URL, SAMPLES

TENDER = (SAMPLES / "sample_tender.txt").read_bytes()
EVIDENCE = json.loads((SAMPLES / "sample_evidence.json").read_text())


def prepared(client, acct):
    h = acct["headers"]
    t = client.post("/v1/tenders", json={"title": "Tender"}, headers=h).json()
    client.post(f"/v1/tenders/{t['id']}/documents", headers=h, files={"file": ("t.txt", TENDER)})
    for e in EVIDENCE:
        client.post("/v1/evidence", headers=h, json={**e, "approved": True})
    q = client.get(f"/v1/tenders/{t['id']}/questions", headers=h).json()[0]
    d = client.post(f"/v1/questions/{q['id']}/drafts", headers=h).json()
    return t, q, d


def test_another_organisation_sees_and_changes_nothing(client, accounts):
    a, b = accounts("Org A"), accounts("Org B")
    t, q, d = prepared(client, a)
    hb = b["headers"]
    assert client.get("/v1/tenders", headers=hb).json() == []
    assert client.get(f"/v1/tenders/{t['id']}/requirements", headers=hb).json() == []
    assert client.get(f"/v1/tenders/{t['id']}/questions", headers=hb).json() == []
    assert client.get("/v1/evidence", headers=hb).json() == []
    assert client.get(f"/v1/drafts/{d['id']}", headers=hb).status_code == 404
    assert client.get(f"/v1/drafts/{d['id']}/provenance", headers=hb).status_code == 404
    assert client.patch(f"/v1/drafts/{d['id']}", headers=hb, json={"text": "hijack"}).status_code == 404
    assert client.post(f"/v1/drafts/{d['id']}/approve", headers=hb).status_code == 404
    assert client.get(f"/v1/tenders/{t['id']}/export", headers=hb).status_code == 404
    assert client.post(f"/v1/questions/{q['id']}/drafts", headers=hb).status_code == 404
    # B cannot upload into A's tender either
    r = client.post(f"/v1/tenders/{t['id']}/documents", headers=hb, files={"file": ("x.txt", TENDER)})
    assert r.status_code == 404
    log = client.get("/v1/audit", headers=hb).json()
    assert log["events_total"] == 1  # only B's own sign-up event


def test_audit_log_rows_are_isolated_at_the_database(client, accounts):
    a, b = accounts("Org A"), accounts("Org B")
    prepared(client, a)
    with tenant_connection(b["org_id"], APP_URL) as conn:
        assert conn.execute("SELECT count(*) FROM audit_events WHERE org_id = %s", (a["org_id"],)).fetchone()[0] == 0


def test_roles_limit_what_people_can_do(client, accounts):
    owner = accounts("Org A")
    t, q, d = prepared(client, owner)
    viewer = {"Authorization": f"Bearer {add_member(uuid.UUID(owner['org_id']), 'v@example.test', 'viewer')['token']}"}
    contrib = {
        "Authorization": f"Bearer {add_member(uuid.UUID(owner['org_id']), 'c@example.test', 'contributor')['token']}"
    }
    assert client.get("/v1/tenders", headers=viewer).status_code == 200
    assert client.post("/v1/tenders", json={"title": "Nope"}, headers=viewer).status_code == 403
    assert client.post(f"/v1/questions/{q['id']}/drafts", headers=viewer).status_code == 403
    assert client.post(f"/v1/questions/{q['id']}/drafts", headers=contrib).status_code == 201
    ev = {**EVIDENCE[0], "approved": True}
    assert client.post("/v1/evidence", headers=contrib, json=ev).status_code == 403  # approving needs a bid manager
    assert client.post(f"/v1/drafts/{d['id']}/approve", headers=contrib).status_code == 403
    assert client.get(f"/v1/tenders/{t['id']}/export", headers=contrib).status_code == 403
    assert client.get("/v1/audit", headers=contrib).status_code == 403


def test_requests_without_valid_credentials_are_refused(client):
    assert client.get("/v1/tenders").status_code == 401
    assert client.get("/v1/tenders", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/v1/tenders", headers={"Authorization": "Basic abc"}).status_code == 401


def test_signup_can_be_switched_off(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "allow_signup", False)
    assert client.post("/v1/signup", json={"org_name": "Org", "email": "x@example.test"}).status_code == 403


def test_duplicate_email_is_refused(client, accounts):
    a = accounts()
    r = client.post("/v1/signup", json={"org_name": "Other Org", "email": a["email"]})
    assert r.status_code == 409


def test_a_fabricated_requirement_fails_verbatim_verification():
    from app.services.requirements import verify_verbatim

    source = "Tenderers must provide a copy of their insurance certificate."
    assert verify_verbatim("Tenderers must provide a copy of their insurance certificate.", source)
    assert not verify_verbatim("Tenderers must hold ISO 9001 and a turnover above 5 million pounds.", source)


def test_deadlines_follow_london_time():
    from app.services.requirements import parse_deadline

    winter = parse_deadline("Tenders must be submitted no later than 12:00 on 14 November 2026.")
    summer = parse_deadline("Tenders must be submitted no later than 12:00 on 14 July 2026.")
    assert winter.utcoffset().total_seconds() == 0 and summer.utcoffset().total_seconds() == 3600


def test_storage_never_writes_outside_its_root(tmp_path):
    from app.services.storage import LocalStore

    store = LocalStore(str(tmp_path))
    key = store.put(uuid.uuid4(), uuid.uuid4(), b"data")
    assert store.get(key) == b"data"
    with pytest.raises(ValueError):
        store.get("../../etc/passwd")


def test_ai_provider_must_be_local_or_in_an_approved_region():
    from app.ai_gateway.provider import get_provider
    from app.ai_gateway.residency import ResidencyError, check_provider
    from app.core.config import settings

    class Remote:
        region = "us-east-1"

    check_provider(get_provider())  # the template provider is local
    with pytest.raises(ResidencyError):
        check_provider(Remote())
    settings.ai_provider, original = "gpt-unadmitted", settings.ai_provider
    try:
        with pytest.raises(RuntimeError):
            get_provider()
    finally:
        settings.ai_provider = original


def test_the_web_page_is_served(client):
    assert client.get("/ui/").status_code == 200
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/ui/"
