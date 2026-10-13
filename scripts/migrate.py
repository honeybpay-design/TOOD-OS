"""Apply SQL migrations in order using the admin connection. Idempotent."""

import os
import pathlib
import sys

import psycopg
from psycopg import sql

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def ensure_roles(conn: psycopg.Connection) -> None:
    for role, env_key in (("app_user", "APP_USER_PASSWORD"), ("auth_user", "AUTH_USER_PASSWORD")):
        password = os.environ.get(env_key)
        if not password:
            sys.exit(f"{env_key} is not set (see .env.example)")
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        verb = "ALTER" if exists else "CREATE"
        conn.execute(
            sql.SQL(f"{verb} ROLE {{}} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {{}}").format(
                sql.Identifier(role), sql.Literal(password)
            )
        )


def main() -> None:
    load_env()
    url = os.environ.get("DATABASE_ADMIN_URL")
    if not url:
        sys.exit("DATABASE_ADMIN_URL is not set (copy .env.example to .env)")
    with psycopg.connect(url, autocommit=True) as conn:
        ensure_roles(conn)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            if path.name in done:
                print(f"skip   {path.name}")
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            print(f"apply  {path.name}")
    print("migrations complete")


if __name__ == "__main__":
    main()
