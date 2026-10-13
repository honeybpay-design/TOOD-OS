"""Installation verification. Exit code 0 only when every check passes."""

import importlib
import os
import pathlib
import sys

import psycopg

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

EXPECTED_TABLES = {
    "organisations",
    "users",
    "memberships",
    "company_profiles",
    "certificates",
    "evidence_items",
    "evidence_chunks",
    "tenders",
    "documents",
    "doc_blocks",
    "requirements",
    "questions",
    "drafts",
    "draft_claims",
    "revisions",
    "approvals",
    "audit_events",
    "daily_anchors",
    "export_manifests",
    "model_cards",
    "jobs",
    "api_tokens",
}
RLS_TABLES = {
    "company_profiles",
    "certificates",
    "evidence_items",
    "evidence_chunks",
    "tenders",
    "documents",
    "doc_blocks",
    "requirements",
    "questions",
    "drafts",
    "draft_claims",
    "revisions",
    "approvals",
    "export_manifests",
    "jobs",
    "organisations",
    "memberships",
    "users",
    "audit_events",
    "api_tokens",
}
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_env()
    check("Python >= 3.12", sys.version_info >= (3, 12), sys.version.split()[0])
    check(".env present", (ROOT / ".env").exists(), "copy .env.example to .env")

    admin_url = os.environ.get("DATABASE_ADMIN_URL", "")
    app_url = os.environ.get("DATABASE_URL", "")
    try:
        admin = psycopg.connect(admin_url, autocommit=True, connect_timeout=3)
        check("Database reachable (admin)", True)
    except Exception as exc:  # noqa: BLE001
        check("Database reachable (admin)", False, str(exc).splitlines()[0])
        return report()

    exts = {r[0] for r in admin.execute("SELECT extname FROM pg_extension")}
    for ext in ("vector", "pg_trgm", "pgcrypto"):
        check(f"Extension {ext}", ext in exts)

    tables = {
        r[0] for r in admin.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    }
    missing = EXPECTED_TABLES - tables
    check("All 22 tables exist", not missing, ", ".join(sorted(missing)))

    forced = {
        r[0]
        for r in admin.execute(
            "SELECT relname FROM pg_class WHERE relrowsecurity AND relforcerowsecurity AND relkind='r'"
        )
    }
    nofr = RLS_TABLES - forced
    check("Forced RLS on all tenant and identity tables", not nofr, ", ".join(sorted(nofr)))

    for role in ("app_user", "auth_user"):
        row = admin.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
        check(f"Role {role} is unprivileged", row == (False, False), str(row))

    trig = {r[0] for r in admin.execute("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")}
    for t in ("revisions_append_only", "audit_append_only", "anchors_append_only"):
        check(f"Trigger {t}", t in trig)

    try:
        with psycopg.connect(app_url, connect_timeout=3) as conn:
            n = conn.execute("SELECT count(*) FROM tenders").fetchone()[0]
        check("Tenant isolation default-deny (no context => 0 rows)", n == 0, f"rows={n}")
    except Exception as exc:  # noqa: BLE001
        check("Connect as app_user", False, str(exc).splitlines()[0])

    try:
        from fastapi.testclient import TestClient

        app = importlib.import_module("app.main").app
        check("API /healthz", TestClient(app).get("/healthz").status_code == 200)
        check("API /readyz (database)", TestClient(app).get("/readyz").status_code == 200)
        workflow(admin, TestClient(app))
    except Exception as exc:  # noqa: BLE001
        check("API importable", False, str(exc).splitlines()[0])

    return report()


def workflow(admin, client) -> None:
    """Sign up, upload the sample tender, add evidence, draft, approve and export, then remove the test data."""
    import io
    import json
    import uuid

    org_id = None
    try:
        email = f"verify-{uuid.uuid4().hex[:8]}@example.test"
        acct = client.post("/v1/signup", json={"org_name": "Install check", "email": email}).json()
        org_id = acct["org_id"]
        h = {"Authorization": f"Bearer {acct['token']}"}
        t = client.post("/v1/tenders", json={"title": "Install check tender"}, headers=h).json()
        sample = (ROOT / "samples" / "sample_tender.txt").read_bytes()
        up = client.post(f"/v1/tenders/{t['id']}/documents", headers=h, files={"file": ("t.txt", sample)}).json()
        for e in json.loads((ROOT / "samples" / "sample_evidence.json").read_text()):
            client.post("/v1/evidence", headers=h, json={**e, "approved": True})
        drafts = [
            client.post(f"/v1/questions/{q['id']}/drafts", headers=h).json()
            for q in client.get(f"/v1/tenders/{t['id']}/questions", headers=h).json()
        ]
        gate = client.get(f"/v1/tenders/{t['id']}/export", headers=h).status_code
        for d in drafts:
            client.post(f"/v1/drafts/{d['id']}/approve", headers=h)
        out = client.get(f"/v1/tenders/{t['id']}/export", headers=h)
        ok = (
            up["requirements"] >= 5
            and up["questions"] == 2
            and gate == 409
            and out.status_code == 200
            and len(io.BytesIO(out.content).getvalue()) > 2000
        )
        check(
            "Workflow: upload, extract, draft, approve, gated export",
            ok,
            f"requirements={up.get('requirements')} gate={gate} export={out.status_code}",
        )
    except Exception as exc:  # noqa: BLE001
        check("Workflow: upload, extract, draft, approve, gated export", False, str(exc)[:120])
    finally:
        if org_id:
            users = [r[0] for r in admin.execute("SELECT user_id FROM memberships WHERE org_id = %s", (org_id,))]
            for tbl, trg in (("revisions", "revisions_append_only"), ("audit_events", "audit_append_only")):
                admin.execute(f"ALTER TABLE {tbl} DISABLE TRIGGER {trg}")
            for tbl in (
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
            ):
                admin.execute(f"DELETE FROM {tbl} WHERE org_id = %s", (org_id,))
            for tbl, trg in (("revisions", "revisions_append_only"), ("audit_events", "audit_append_only")):
                admin.execute(f"ALTER TABLE {tbl} ENABLE TRIGGER {trg}")
            for u in users:
                admin.execute("DELETE FROM users WHERE id = %s", (u,))
            admin.execute("DELETE FROM organisations WHERE id = %s", (org_id,))


def report() -> int:
    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {'' if ok else detail}")
        failed += 0 if ok else 1
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
