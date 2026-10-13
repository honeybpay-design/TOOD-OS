#!/usr/bin/env bash
# One-command local setup (macOS, Linux, WSL). Run from the repository root.
set -euo pipefail
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v docker  >/dev/null || { echo "docker is required"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e "apps/api[dev]"
[ -f .env ] || cp .env.example .env
docker compose up -d --wait
python scripts/migrate.py
python scripts/verify_install.py
