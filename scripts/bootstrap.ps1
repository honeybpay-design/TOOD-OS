# One-command local setup for Windows PowerShell. Run from the repository root.
$ErrorActionPreference = "Stop"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python is required" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "docker is required" }
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install -q --upgrade pip
pip install -q -e "apps/api[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --wait
python scripts/migrate.py
python scripts/verify_install.py
