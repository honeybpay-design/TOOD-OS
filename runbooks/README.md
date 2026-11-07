# Runbooks

Create one file per procedure before release: provider outage, failed parse, suspected breach,
deletion failure, rollback, restore (blueprint section 26).


## Current procedures (26 October2026)

- [PostgreSQL16.15 alignment/cutover/restore boundaries](postgresql16-cutover.md)
- [Document storage, parsing readiness and legacy-original recovery](document-storage-recovery.md)

These record verified work and explicit pending approvals/gates; they do not authorize a production action. Provider outage, suspected breach and other remaining procedures still need their own reviewed runbooks before release.

## F34 legacy migration CLI warning — 27 October 2026

Do not use `python scripts/migrate.py --help` as a harmless probe: the canonical script currently ignores arguments and can load root.env and attempt role/schema writes. Actual offline fake-sink reproduction reached2role-credentialDDL and the trackerDDL with argv--help; no real database was connected. Current pytest/installer guards do not protect this separate CLI or legacy bootstrap call. Use only the reviewed guarded synthetic driver for current tests; any real migration needs separate approved tooling/target review. Evidence: audit/evidence/2026-10-25/migration-cli-safety-31/F34.md. No migration script fix is applied by this warning.
