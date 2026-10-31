import uuid

import psycopg
import pytest
from app.core.tenant import tenant_connection
from app.provenance.hashchain import compute_hash
from conftest import APP_URL
from psycopg.types.json import Jsonb


def _make_revision(admin, org):
    admin.execute(
        "INSERT INTO questions (id, org_id, tender_id, prompt) "
        "SELECT gen_random_uuid(), %s, id, 'q' FROM tenders WHERE org_id = %s",
        (org, org),
    )
    qid = admin.execute("SELECT id FROM questions WHERE org_id = %s", (org,)).fetchone()[0]
    did = uuid.uuid4()
    admin.execute(
        "INSERT INTO drafts (id, org_id, question_id, version, content) VALUES (%s, %s, %s, 1, '{}')", (did, org, qid)
    )
    # Retained fixtures must not reuse a globally unique hash from a prior test.
    content = {"text": f"append-only fixture {did}"}
    digest = compute_hash(content, {"actor": "None", "seq": 1}, None)
    admin.execute(
        "INSERT INTO revisions (org_id, draft_id, seq, hash, content_snapshot, origin_spans) "
        "VALUES (%s, %s, 1, %s, %s, '[]')",
        (org, did, digest, Jsonb(content)),
    )
    return did


def test_revisions_cannot_be_updated_or_deleted_by_app(admin, two_orgs):
    _make_revision(admin, two_orgs["a"])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with tenant_connection(two_orgs["a"], APP_URL) as conn:
            conn.execute("UPDATE revisions SET hash = %s", ("b" * 64,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with tenant_connection(two_orgs["a"], APP_URL) as conn:
            conn.execute("DELETE FROM revisions")


def test_trigger_blocks_even_the_admin_role(admin, two_orgs):
    _make_revision(admin, two_orgs["b"])
    with pytest.raises(psycopg.errors.RaiseException):
        admin.execute("UPDATE revisions SET hash = %s WHERE org_id = %s", ("c" * 64, two_orgs["b"]))
