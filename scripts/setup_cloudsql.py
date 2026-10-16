#!/usr/bin/env python
"""Setup Cloud SQL database: create roles, run migrations, update secrets.

Run AFTER Cloud SQL instance is created and running.
Usage: python scripts/setup_cloudsql.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Cloud SQL settings
PROJECT = "tood-os"
REGION = "europe-west2"
INSTANCE = "tood-os-instance"
INSTANCE_REGION = "us-east4"  # existing instance location
DB_NAME = "tood"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
APP_PASSWORD = os.environ.get("APP_USER_PASSWORD", "")
AUTH_PASSWORD = os.environ.get("AUTH_USER_PASSWORD", "")

INSTANCE_CONNECTION = f"{PROJECT}:{INSTANCE_REGION}:{INSTANCE}"


GCLOUD = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"


def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Replace 'gcloud' with full path
    if cmd[0] == "gcloud":
        cmd = [GCLOUD] + cmd[1:]
    print(f"  $ {' '.join(cmd[:6])}...")
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def main() -> None:
    print("=" * 60)
    print("Cloud SQL Setup — TOOD-OS")
    print("=" * 60)

    # 1. Create database
    print("\n[1] Creating database 'tood'...")
    r = run(
        ["gcloud", "sql", "databases", "create", DB_NAME, "--instance", INSTANCE, "--project", PROJECT], check=False
    )
    if r.returncode == 0:
        print("  OK   database created")
    else:
        print("  SKIP database may already exist")

    # 2. Create app_user
    print("\n[2] Creating app_user...")
    r = run(
        [
            "gcloud",
            "sql",
            "users",
            "create",
            "app_user",
            "--instance",
            INSTANCE,
            "--password",
            APP_PASSWORD,
            "--project",
            PROJECT,
        ],
        check=False,
    )
    print("  OK" if r.returncode == 0 else "  SKIP (may exist)")

    # 3. Create auth_user
    print("\n[3] Creating auth_user...")
    r = run(
        [
            "gcloud",
            "sql",
            "users",
            "create",
            "auth_user",
            "--instance",
            INSTANCE,
            "--password",
            AUTH_PASSWORD,
            "--project",
            PROJECT,
        ],
        check=False,
    )
    print("  OK" if r.returncode == 0 else "  SKIP (may exist)")

    # 4. Get public IP
    print("\n[4] Getting Cloud SQL public IP...")
    r = run(
        [
            "gcloud",
            "sql",
            "instances",
            "describe",
            INSTANCE,
            "--project",
            PROJECT,
            "--format=value(ipAddresses[0].ipAddress)",
        ]
    )
    ip = r.stdout.strip()
    print(f"  IP: {ip}")

    # 5. Build connection strings
    admin_url = f"postgresql://postgres:{ADMIN_PASSWORD}@{ip}:5432/{DB_NAME}"
    app_url = f"postgresql://app_user:{APP_PASSWORD}@{ip}:5432/{DB_NAME}"
    auth_url = f"postgresql://auth_user:{AUTH_PASSWORD}@{ip}:5432/{DB_NAME}"

    # Cloud Run uses Unix socket via Cloud SQL connector
    cloud_run_app_url = f"postgresql://app_user:{APP_PASSWORD}@/{DB_NAME}?host=/cloudsql/{INSTANCE_CONNECTION}"
    cloud_run_admin_url = f"postgresql://postgres:{ADMIN_PASSWORD}@/{DB_NAME}?host=/cloudsql/{INSTANCE_CONNECTION}"
    cloud_run_auth_url = f"postgresql://auth_user:{AUTH_PASSWORD}@/{DB_NAME}?host=/cloudsql/{INSTANCE_CONNECTION}"

    print(f"\n  Admin URL (direct): {admin_url[:60]}...")
    print(f"  App URL (Cloud Run): {cloud_run_app_url[:60]}...")

    # 6. Authorize local IP for migrations
    print("\n[5] Authorizing local machine IP for migration...")
    import urllib.request

    try:
        local_ip = urllib.request.urlopen("https://api.ipify.org").read().decode()
        run(
            [
                "gcloud",
                "sql",
                "instances",
                "patch",
                INSTANCE,
                "--authorized-networks",
                f"{local_ip}/32",
                "--project",
                PROJECT,
            ],
            check=False,
        )
        print(f"  Authorized: {local_ip}")
    except Exception as e:  # noqa: BLE001
        print(f"  WARN: could not get local IP: {e}")

    # 7. Update .env with cloud URLs (keep local URLs as backup)
    print("\n[6] Writing cloud connection strings to .env.cloud...")
    env_cloud = ROOT / ".env.cloud"
    env_cloud.write_text(
        f"# Cloud SQL connection strings — use for production\n"
        f"DATABASE_ADMIN_URL={admin_url}\n"
        f"DATABASE_URL={app_url}\n"
        f"AUTH_DATABASE_URL={auth_url}\n"
        f"APP_USER_PASSWORD={APP_PASSWORD}\n"
        f"AUTH_USER_PASSWORD={AUTH_PASSWORD}\n"
        f"\n# Cloud Run (Unix socket) — use in Secret Manager\n"
        f"CLOUD_RUN_DATABASE_URL={cloud_run_app_url}\n"
        f"CLOUD_RUN_DATABASE_ADMIN_URL={cloud_run_admin_url}\n"
        f"CLOUD_RUN_AUTH_DATABASE_URL={cloud_run_auth_url}\n"
        f"CLOUD_SQL_INSTANCE={INSTANCE_CONNECTION}\n"
    )
    print("  Written to .env.cloud")

    # 8. Run migrations using direct IP connection
    print("\n[7] Running migrations against Cloud SQL...")
    env = os.environ.copy()
    env["DATABASE_ADMIN_URL"] = admin_url
    env["APP_USER_PASSWORD"] = APP_PASSWORD
    env["AUTH_USER_PASSWORD"] = AUTH_PASSWORD
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    result = subprocess.run(
        [str(venv_python), "scripts/migrate.py"], check=False, cwd=ROOT, env=env, capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:500]}")
        sys.exit(1)

    # 9. Update Secret Manager with Cloud Run URLs
    print("\n[8] Updating Secret Manager with Cloud Run connection strings...")
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{PROJECT}"

        updates = {
            "database-url": cloud_run_app_url,
            "auth-database-url": cloud_run_auth_url,
            "app-user-password": APP_PASSWORD,
            "auth-user-password": AUTH_PASSWORD,
        }
        for secret_id, value in updates.items():
            secret_name = f"{parent}/secrets/{secret_id}"
            client.add_secret_version(
                parent=secret_name,
                payload={"data": value.encode()},
            )
            print(f"  OK   {secret_id} updated")
    except Exception as e:  # noqa: BLE001
        print(f"  WARN: could not update Secret Manager: {e}")
        print("  Manual update needed — see .env.cloud for values")

    print("\n" + "=" * 60)
    print("Cloud SQL setup complete!")
    print(f"  Instance: {INSTANCE_CONNECTION}")
    print(f"  Public IP: {ip}")
    print(f"  Database: {DB_NAME}")
    print("\nNext steps:")
    print("  1. Deploy API: gcloud run deploy tood-os-api ... --add-cloudsql-instances=" + INSTANCE_CONNECTION)
    print("  2. Setup Stripe webhook: https://api.tood.uk/v1/billing/webhook")
    print("  3. Setup DNS at Fasthosts: TOOD.UK → Cloud Run URLs")


if __name__ == "__main__":
    main()
