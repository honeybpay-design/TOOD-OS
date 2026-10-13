# TOOD-OS

Trusted, Orchestrated, Observable Document Operating System for UK public-sector procurement.
Specification: **TOOD-OS Full Master Blueprint v1.1** (Honey-B2024 Ltd).

This repository installs and **runs**: a working application with sign-up, tender upload (PDF, Word, text),
requirement extraction with verbatim checks, an evidence library, drafting with claim verification, provenance
and a hash chain, named approval, a gated Word export, and an audit log. It sits on a database with forced
row-level security and append-only assurance tables. Drafting uses a local template provider until a real
model is connected and admitted (see `AGENTS.md`).

## Quick start

Prerequisites: Git, Python 3.12+, Node 20+, Docker Desktop, VS Code.

| System | Command |
|---|---|
| Windows PowerShell | `./scripts/bootstrap.ps1` |
| macOS, Linux, WSL | `./scripts/bootstrap.sh` |

Success looks like `17/17 checks passed`. Then run `cd apps/api && pytest -q` (expect `44 passed`, none skipped).

## Run it

```
cd apps/api
uvicorn app.main:app --port 8000
```

Open http://localhost:8000. Create a workspace, then upload `samples/sample_tender.txt`, click
"Load sample evidence", draft both answers, approve them and export the Word file. Or run
`python scripts/demo.py` (with the server running) to do the same from the command line.

## For AI agents
Open `AGENTS.md`, then work through `docs/agent-tasks.md`. Record results in `docs/install-report.md`.

## For the development team
Run `docs/test-plan.md` (D01 to D19) before any use. Nothing here is production-ready until the
blueprint's gates (section 28) and release checklist (section 35) are met.

## Local services
PostgreSQL 16 with pgvector `:5432`. Uploaded files are stored on local disk under `data/uploads` until a cloud
storage backend is chosen (`app/services/storage.py` defines the two-method interface to implement).
Local credentials in `.env.example` are for development only.
