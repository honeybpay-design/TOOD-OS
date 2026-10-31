import psycopg
import pytest
from app.core.tenant import tenant_connection
from conftest import APP_URL


def test_tenant_sees_only_own_rows(two_orgs):
    with tenant_connection(two_orgs["a"], APP_URL) as conn:
        titles = [r[0] for r in conn.execute("SELECT title FROM tenders")]
    assert "tender-a" in titles and "tender-b" not in titles


def test_no_context_returns_zero_rows(two_orgs):
    with psycopg.connect(APP_URL) as conn:
        assert conn.execute("SELECT count(*) FROM tenders").fetchone()[0] == 0


def test_cross_tenant_insert_is_rejected(two_orgs):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with tenant_connection(two_orgs["a"], APP_URL) as conn:
            conn.execute("INSERT INTO tenders (org_id, title) VALUES (%s, 'intruder')", (two_orgs["b"],))


def test_context_does_not_leak_between_transactions(two_orgs):
    with tenant_connection(two_orgs["a"], APP_URL):
        pass
    with psycopg.connect(APP_URL) as conn:
        assert conn.execute("SELECT count(*) FROM tenders").fetchone()[0] == 0


def test_app_user_cannot_see_other_organisations(two_orgs):
    with tenant_connection(two_orgs["a"], APP_URL) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM organisations")]
    assert names == ["test-a"]


def test_app_role_has_no_elevated_privileges(admin):
    row = admin.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app_user'").fetchone()
    assert row == (False, False)
