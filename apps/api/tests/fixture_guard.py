"""Fail-closed controls for owned, disposable synthetic PostgreSQL tests only."""

import re
from urllib.parse import urlsplit


class FixtureGuardError(RuntimeError):
    """Messages are deliberately fixed and never contain a supplied DSN/secret."""


TRIGGERS = {
    ("revisions", "revisions_append_only", "O"),
    ("audit_events", "audit_append_only", "O"),
    ("daily_anchors", "anchors_append_only", "O"),
}
RLS_TABLES = {"tenders", "revisions", "audit_events", "subscriptions", "api_tokens"}


def guard_environment(env):
    required = {
        "TOOD_TEST_SUITE_ONLY": "true",
        "AI_PROVIDER": "template",
        "STORAGE_BACKEND": "local",
        "GCP_PROJECT": "synthetic-no-cloud",
        "GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent/synthetic-audit-credentials.json",
        "TOOD_TEST_EVIDENCE_DIR": "/results",
    }
    if any(env.get(k) != v for k, v in required.items()):
        raise FixtureGuardError("Explicit isolated synthetic test settings are required")
    nonce = env.get("TOOD_TEST_RUN_ID", "")
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise FixtureGuardError("A fresh synthetic run identity is required")
    if any(k.startswith("PG") for k in env):
        raise FixtureGuardError("Ambient libpq settings are forbidden for this test driver")
    forbidden = (
        "GOOGLE_CLIENT_SECRET",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
    )
    if any(env.get(k) for k in forbidden):
        raise FixtureGuardError("Real provider credentials are forbidden in synthetic tests")
    roles = {"DATABASE_ADMIN_URL": "postgres", "DATABASE_URL": "app_user", "AUTH_DATABASE_URL": "auth_user"}
    for key, role in roles.items():
        try:
            url = urlsplit(env.get(key, ""))
            safe = (
                url.scheme == "postgresql"
                and url.hostname == "synthetic-db"
                and url.port == 5432
                and url.path == "/postgres"
                and url.username == role
                and url.password is None
                and not url.query
                and not url.fragment
            )
        except ValueError:
            safe = False
        if not safe:
            raise FixtureGuardError("Only the driver-owned internal database URLs are accepted")
    return nonce


def assert_controls(conn):
    triggers = set(
        conn.execute(
            "SELECT c.relname,t.tgname,t.tgenabled FROM pg_catalog.pg_trigger t "
            "JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid "
            "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND t.tgname=ANY(%s)",
            ([x[1] for x in TRIGGERS],),
        ).fetchall()
    )
    if triggers != TRIGGERS:
        raise FixtureGuardError("Append-only controls are missing or disabled")
    roles = conn.execute(
        "SELECT rolname,rolsuper,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname IN ('app_user','auth_user')"
    ).fetchall()
    if {r[0] for r in roles} != {"app_user", "auth_user"} or any(r[1] or r[2] for r in roles):
        raise FixtureGuardError("Application test roles must not bypass tenant security")
    rls = conn.execute(
        "SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity FROM pg_catalog.pg_class c "
        "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relname=ANY(%s)",
        (sorted(RLS_TABLES),),
    ).fetchall()
    if {r[0] for r in rls} != RLS_TABLES or any(not r[1] or not r[2] for r in rls):
        raise FixtureGuardError("Forced tenant RLS is missing from a guarded table")
    return {"append_triggers_enabled": 3, "roles_not_superuser_or_bypassrls": 2, "forced_rls_tables": 5}


def verify_database(conn, nonce):
    identity = conn.execute("SELECT current_setting('server_version'),current_database(),current_user").fetchone()
    if not identity or not identity[0].startswith("16.15") or identity[1:] != ("postgres", "postgres"):
        raise FixtureGuardError("Unexpected synthetic database version or identity")
    rows = conn.execute(
        "SELECT run_id FROM audit_test_only.run_identity "
        "WHERE singleton IS TRUE AND created_at > clock_timestamp()-interval '1 hour'"
    ).fetchall()
    if rows != [(nonce,)]:
        raise FixtureGuardError("Disposable database marker is missing, stale or mismatched")
    return assert_controls(conn)
