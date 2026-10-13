# Installation tasks for AI agents (run in order)

Each task has a goal, steps and an acceptance check. Stop at the first failed check and report it.

## T00 Prerequisites
Goal: the machine can run the stack.
Steps: confirm `git --version`, `python --version` (3.12 or newer), `node --version` (20 or newer),
`docker --version` and `docker compose version`. Open the folder in VS Code and accept the recommended extensions.
Accept: all versions print and meet the minimum.

## T01 Bootstrap
Goal: virtual environment, dependencies, local stack and database ready.
Steps: Windows PowerShell `./scripts/bootstrap.ps1`; macOS, Linux or WSL `./scripts/bootstrap.sh`.
Accept: output ends with `17/17 checks passed`.

## T02 Test suite
Goal: the foundation behaves as specified.
Steps: `cd apps/api && pytest -q`.
Accept: `44 passed`, with 0 failed and 0 skipped. A skip means the database was unreachable, which is a failure.

## T03 Run the API
Steps: run the "API: run" task, then open `http://localhost:8000/healthz`, `/readyz` and `/docs`.
Then run `python scripts/demo.py` in a second terminal and open http://localhost:8000 in a browser.
Accept: `/healthz` returns `{"status":"ok"}`, `/readyz` returns `{"status":"ready"}`, `/docs` loads, the demo prints `export 200` and saves `data/demo_submission.docx`, and the page shows the sign-up form.

## T04 Clean rebuild
Goal: the install is repeatable.
Steps: `docker compose down -v`, then run T01 again.
Accept: T01 and T02 pass again from a clean state. Running `python scripts/migrate.py` twice prints `skip` for every file the second time.

## T05 Web application
Steps: delete `apps/web/.gitkeep`, then
`npx create-next-app@latest apps/web --typescript --tailwind --eslint --app --use-npm --no-src-dir --import-alias "@/*"`,
then `cd apps/web && npx shadcn@latest init`.
Accept: `cd apps/web && npm run build` succeeds. Record the installed versions in the install report.

## T06 API client
Steps: `python scripts/export_openapi.py`, then
`npx openapi-typescript packages/api-client/openapi.json -o packages/api-client/schema.d.ts`.
Accept: both files exist and `npm run build` in `apps/web` still succeeds.

## T07 Continuous integration
Steps: push a branch, open a pull request.
Accept: every job in `.github/workflows/ci.yml` is green.

## T08 Install report
Steps: copy the command outputs for T01 to T07 into `docs/install-report.md`.
Accept: every row has a result and a date.

## T09 Hand-over
Steps: open a pull request with the install report; a human reviews and merges; tag the commit `install-verified`.
Accept: the tag exists and `docs/test-plan.md` is ready for the development team.
