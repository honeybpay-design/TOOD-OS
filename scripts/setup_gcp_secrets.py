#!/usr/bin/env python
"""Plan Secret Manager provisioning by default, without file reads or GCP access.

Real access requires --confirm-write, --project and --env-file.
Never print values or exception details that might contain credentials.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Keys to push to Secret Manager (never push plain DB admin creds or raw .env)
SECRET_KEYS = [
    "DATABASE_URL",
    "AUTH_DATABASE_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
    "APP_USER_PASSWORD",
    "AUTH_USER_PASSWORD",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_STARTER",
    "STRIPE_PRICE_PROFESSIONAL",
    "STRIPE_PRICE_ENTERPRISE",
    "AI_PROVIDER",
    "GCP_PROJECT",
    "GCP_REGION",
    "AI_ALLOWED_REGIONS",
    "OPENAI_API_KEY",
]

def load_env(path: pathlib.Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            # Last value wins (handles duplicates)
            env[k] = v
    return env


def _make_client():
    from google.api_core.exceptions import NotFound
    from google.cloud import secretmanager

    return secretmanager.SecretManagerServiceClient(), NotFound


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan secret provisioning; no GCP access by default")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="list names without reading files or contacting GCP (default)")
    mode.add_argument("--confirm-write", action="store_true", help="explicitly permit GCP reads and writes for this invocation")
    parser.add_argument("--project", help="explicit target project; no production default")
    parser.add_argument("--env-file", type=pathlib.Path, help="explicit local input file; values are never printed")
    args = parser.parse_args(argv)
    if not args.confirm_write:
        print("DRY RUN: no environment files read; no GCP client or resource access")
        print(f"Target project: {args.project or '(not selected)'}")
        for key in SECRET_KEYS:
            print(f"PLAN {key} -> {key.lower().replace('_', '-')}")
        return 0

    if not args.project or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", args.project):
        parser.error("--confirm-write requires an explicit valid --project")
    if not args.env_file:
        parser.error("--confirm-write requires an explicit --env-file")
    try:
        env = load_env(args.env_file)
    except (OSError, UnicodeError):
        print("ERROR: cannot read the explicitly selected environment file", file=sys.stderr)
        return 1
    try:
        client, not_found = _make_client()
    except Exception:
        print("ERROR: cannot initialize the secret client; details suppressed", file=sys.stderr)
        return 1
    parent = f"projects/{args.project}"
    processed = 0
    for key in SECRET_KEYS:
        value = env.get(key)
        if not value:
            print(f"SKIP {key}: no value supplied")
            continue
        secret_id = key.lower().replace("_", "-")
        secret_name = f"{parent}/secrets/{secret_id}"
        try:
            try:
                client.get_secret(name=secret_name)
            except not_found:
                client.create_secret(
                    parent=parent, secret_id=secret_id,
                    secret={"replication": {"automatic": {}}},
                )
            client.add_secret_version(parent=secret_name, payload={"data": value.encode()})
        except Exception:
            print(f"ERROR: provisioning failed for {key}; details suppressed", file=sys.stderr)
            return 1
        processed += 1
        print(f"OK {key} -> {secret_id}")
    print(f"Completed {processed} configured secret names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
