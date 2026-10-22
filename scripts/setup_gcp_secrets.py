#!/usr/bin/env python
"""Push .env secrets to Google Cloud Secret Manager for Cloud Run deployment.

Usage: python scripts/setup_gcp_secrets.py
Requires: gcloud auth application-default login (already done)
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Keys to push to Secret Manager (never push plain DB admin creds or raw .env)
SECRET_KEYS = [
    "DATABASE_URL",
    "AUTH_DATABASE_URL",
    "APP_USER_PASSWORD",
    "AUTH_USER_PASSWORD",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_STARTER",
    "STRIPE_PRICE_PROFESSIONAL",
    "STRIPE_PRICE_ENTERPRISE",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
    "AI_PROVIDER",
    "GCP_PROJECT",
    "GCP_REGION",
    "AI_ALLOWED_REGIONS",
    "OPENAI_API_KEY",
]

PROJECT = "tood-os"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            # Last value wins (handles duplicates)
            env[k] = v
    return env


def main() -> None:
    try:
        from google.cloud import secretmanager
    except ImportError:
        sys.exit("google-cloud-secret-manager not installed. Run: pip install google-cloud-secret-manager")

    env = load_env()
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT}"

    print(f"Pushing secrets to {parent}\n")

    for key in SECRET_KEYS:
        value = env.get(key)
        if not value:
            print(f"  SKIP  {key} (not in .env)")
            continue

        secret_id = key.lower().replace("_", "-")
        secret_name = f"{parent}/secrets/{secret_id}"

        # Create secret if it doesn't exist
        try:
            client.get_secret(name=secret_name)
        except Exception:  # noqa: BLE001
            client.create_secret(
                parent=parent,
                secret_id=secret_id,
                secret={"replication": {"automatic": {}}},
            )

        # Add new version
        client.add_secret_version(
            parent=secret_name,
            payload={"data": value.encode()},
        )
        print(f"  OK    {key} → {secret_id}")

    print(f"\nDone. {len(SECRET_KEYS)} secrets processed.")
    print("\nNext: run scripts/deploy.sh to deploy to Cloud Run")


if __name__ == "__main__":
    main()
