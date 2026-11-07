"""Configured tests run only through the owned disposable synthetic driver.

No root.env/default URL loading and no row cleanup that bypasses append-only controls.
"""

import json
import os
import pathlib
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient
from fixture_guard import FixtureGuardError, assert_controls, guard_environment, verify_database

ROOT = pathlib.Path(__file__).resolve().parents[3]
try:
    RUN_ID = guard_environment(os.environ)
    if not pathlib.Path("/.dockerenv").is_file() or (ROOT / ".env").exists():
        raise FixtureGuardError("Use the isolated driver without a repository environment mount")
except FixtureGuardError as exc:
    raise pytest.UsageError(str(exc)) from None
ADMIN_URL = os.environ["DATABASE_ADMIN_URL"]
APP_URL = os.environ["DATABASE_URL"]
SAMPLES = ROOT / "samples"
EVIDENCE = pathlib.Path("/results")


def _verified_connection():
    conn = None
    try:
        conn = psycopg.connect(
            ADMIN_URL, autocommit=True, connect_timeout=3, options="-c default_transaction_read_only=on"
        )
        proof = verify_database(conn, RUN_ID)
        # Marker and all mandatory controls were verified before any write can occur.
        conn.execute("SET default_transaction_read_only = off")
        return conn, proof
    except Exception as exc:
        if conn is not None:
            conn.close()
        raise pytest.UsageError("Synthetic database guard failed: " + type(exc).__name__) from None


def pytest_sessionstart(session):
    conn, proof = _verified_connection()
    conn.close()
    (EVIDENCE / "fixture-initial-control-proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")


@pytest.fixture(scope="session")
def admin():
    conn, _ = _verified_connection()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def preserve_controls(admin, request):
    for phase in ("before", "after"):
        proof = assert_controls(admin)
        with (EVIDENCE / "fixture-control-checks.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps({"test": request.node.nodeid, "phase": phase, **proof}) + "\n")
        if phase == "before":
            yield


@pytest.fixture()
def two_orgs(admin):
    """Retain UUID-isolated tenants until the whole labelled tmpfs database is removed."""
    ids = {}
    for key in ("a", "b"):
        org = uuid.uuid4()
        admin.execute("INSERT INTO organisations (id,name) VALUES (%s,%s)", (org, f"test-{key}"))
        admin.execute("INSERT INTO tenders (org_id,title) VALUES (%s,%s)", (org, f"tender-{key}"))
        ids[key] = org
    return ids


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "uploads"))
    # Enter the lifespan so declared parsers/startup controls really execute.
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def accounts(admin, client):
    """Create isolated fictional tenants; preserve their immutable history for the run."""

    def make(name="Acme Bids Ltd"):
        email = f"{uuid.uuid4().hex[:10]}@example.test"
        response = client.post("/v1/signup", json={"org_name": name, "email": email})
        assert response.status_code == 201, response.text
        data = response.json()
        return {
            "headers": {"Authorization": f"Bearer {data['token']}"},
            "org_id": data["org_id"],
            "user_id": data["user_id"],
            "email": email,
        }

    return make
