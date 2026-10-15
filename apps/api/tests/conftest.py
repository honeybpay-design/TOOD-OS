import os
import pathlib
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[3]
env = ROOT / ".env"
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ADMIN_URL = os.environ.get("DATABASE_ADMIN_URL", "postgresql://postgres:tood_dev_admin@localhost:5432/tood")
APP_URL = os.environ.get("DATABASE_URL", "postgresql://app_user:tood_dev_app@localhost:5432/tood")
SAMPLES = ROOT / "samples"

CUSTOMER_TABLES = [
    "approvals",
    "draft_claims",
    "revisions",
    "drafts",
    "questions",
    "requirements",
    "doc_blocks",
    "documents",
    "evidence_chunks",
    "evidence_items",
    "export_manifests",
    "audit_events",
    "api_tokens",
    "memberships",
    "tenders",
    "company_profiles",
    "jobs",
    "certificates",
]


@pytest.fixture(scope="session")
def admin():
    try:
        conn = psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=3)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"database not reachable: {exc}")
    yield conn
    conn.close()


def _delete_org(admin, org):
    user_ids = [r[0] for r in admin.execute("SELECT user_id FROM memberships WHERE org_id = %s", (org,))]
    for trig_table, trig in (("revisions", "revisions_append_only"), ("audit_events", "audit_append_only")):
        admin.execute(f"ALTER TABLE {trig_table} DISABLE TRIGGER {trig}")
    for table in CUSTOMER_TABLES:
        admin.execute(f"DELETE FROM {table} WHERE org_id = %s", (org,))
    for trig_table, trig in (("revisions", "revisions_append_only"), ("audit_events", "audit_append_only")):
        admin.execute(f"ALTER TABLE {trig_table} ENABLE TRIGGER {trig}")
    for u in user_ids:
        admin.execute("DELETE FROM users WHERE id = %s", (u,))
    admin.execute("DELETE FROM organisations WHERE id = %s", (org,))


@pytest.fixture()
def two_orgs(admin):
    """Two organisations, each with one tender, created through the admin role."""
    ids = {}
    for key in ("a", "b"):
        org = uuid.uuid4()
        admin.execute("INSERT INTO organisations (id, name) VALUES (%s, %s)", (org, f"test-{key}"))
        admin.execute("INSERT INTO tenders (org_id, title) VALUES (%s, %s)", (org, f"tender-{key}"))
        ids[key] = org
    yield ids
    for org in ids.values():
        _delete_org(admin, org)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "uploads"))
    return TestClient(app)


@pytest.fixture()
def accounts(admin, client):
    """Factory: create a fresh organisation and return its token headers. Everything is deleted afterwards."""
    created = []

    def make(name="Acme Bids Ltd"):
        email = f"{uuid.uuid4().hex[:10]}@example.test"
        r = client.post("/v1/signup", json={"org_name": name, "email": email})
        assert r.status_code == 201, r.text
        data = r.json()
        created.append(data["org_id"])
        return {
            "headers": {"Authorization": f"Bearer {data['token']}"},
            "org_id": data["org_id"],
            "user_id": data["user_id"],
            "email": email,
        }

    yield make
    for org in created:
        _delete_org(admin, org)
