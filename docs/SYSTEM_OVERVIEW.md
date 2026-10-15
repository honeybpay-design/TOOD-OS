# TOOD — System Overview
*Trusted Operations & Organised Documents*

Version: 0.2.0 | Date: 2026-10-13

---

## What is TOOD?

TOOD is a web-based procurement writing platform built for UK public-sector suppliers. It helps bid managers and procurement officers prepare compliant tender responses by extracting requirements verbatim from tender documents, generating evidence-grounded draft answers using AI, enforcing human approval before any answer is included in an export, and recording every action in a hash-chained audit log.

The platform is designed to support compliance with the Procurement Act 2023 and related procurement policy notes (PPNs). It does not submit bids automatically — no response is ever sent without explicit named human approval.

---

## Who is it for?

TOOD serves UK organisations that respond to public-sector tenders:

- **Bid managers and bid writers** who need to produce compliant, auditable tender responses.
- **Procurement officers** responsible for approving submissions and maintaining audit records.
- **Compliance and governance teams** who need to demonstrate that AI-assisted drafting is transparent and supervised.
- **SMEs and consultancies** competing for public contracts under the Procurement Act 2023 framework.

---

## Core Capabilities (verified features)

The following capabilities are present in the codebase and verified by the test suite (44 tests passing, 17/17 install checks):

### Requirement extraction (verbatim, source-referenced)
TOOD parses uploaded tender documents (PDF, DOCX, plain text up to 20 MB) and extracts requirements word-for-word from the source text. Each extracted requirement carries a reference to the source document, page number, and block. A verbatim check confirms the extracted text actually appears in the source block — any candidate that fails this check is discarded, not silently included.

### Evidence-based AI drafting
Draft answers are generated using only items from the organisation's approved evidence library. The system uses either Gemini 2.5 Pro (via Vertex AI) or a local template provider (no external AI call). Every AI-generated segment is tagged with the evidence items it drew from. Evidence that has not been explicitly approved by a bid manager cannot be used in drafting.

### Claim verification
After a draft is generated or edited, the system inspects every factual claim (numbers, certifications, statistics, company names) against the evidence library. Claims that cannot be matched to approved evidence are flagged as `unsupported` and block export until they are acknowledged by a named bid manager or removed.

### Named approval workflow
No draft can be included in an export until a named human (bid_manager role or above) explicitly approves it. Approvals are tied to a specific revision hash, so approving one version does not silently carry over to a later edit.

### Gated export (Word .docx)
Export is blocked unless every question has a latest draft, every draft is approved, every unsupported claim is acknowledged, and no draft exceeds its word limit. Only when all conditions are met does the system generate a Word submission pack. The export file's SHA-256 hash is recorded alongside the revision hashes for each answer.

### Hash-chained audit trail
Every draft revision is stored in an append-only `revisions` table with a hash chain (each entry includes the previous entry's hash). Separately, all user actions (uploads, draft generation, edits, approvals, exports) are recorded in an append-only `audit_events` table. The chain can be verified programmatically via `GET /v1/audit`. The database enforces append-only behaviour through triggers — rows cannot be updated or deleted.

### Multi-tenant (row-level security)
The database enforces row-level security on all tenant tables. Every query runs inside a tenant transaction using `tenant_connection()`, which sets the tenant context securely. No query can return data from another organisation.

---

## Compliance Positioning

TOOD is built to align with the following UK procurement regulations. The platform does not claim certified compliance — alignment means the system is designed to support these requirements, and buyers or auditors should evaluate the specific implementation against their requirements.

### Procurement Act 2023
Replaces the Public Contracts Regulations 2015. TOOD helps suppliers structure responses to meet the updated evaluation criteria and transparency obligations.

### PPN 01/17 — Social Value
Policy note requiring social value to be weighted in procurement decisions. TOOD's evidence library is designed to ensure that social value claims are sourced from actual evidence items, not invented at drafting time.

### PPN 02/24 — AI in Procurement
Requires that AI use in procurement is transparent, human-supervised, and auditable. TOOD addresses this through: named approval (a human must approve every response), a full hash-chained audit log, and the rule that no bid is submitted automatically under any circumstances.

---

## Current Limitations (honest)

The following gaps are known as of version 0.2.0:

- **Google OAuth not yet tested in production.** The OAuth implementation is complete (migration 0006, routes, login page) but has not been exercised against the live GCP OAuth consent screen. Manual action is required before first login.
- **Migration 0006 pending on Cloud SQL.** Migrations 0001–0005 were confirmed applied to Cloud SQL in a previous phase. Migration 0006 (OAuth tables) could not be applied due to a connection timeout. Must be run manually when Cloud SQL is accessible.
- **API Cloud Run deployment not confirmed running.** The deploy script and Cloud Run service definitions exist, but a live end-to-end check of the deployed API has not been performed.
- **DNS not configured.** The domain `tood.uk` is registered at Fasthosts but DNS records pointing to Cloud Run have not been configured. The site is not publicly accessible at this address.
- **Cloud SQL in us-east4, not europe-west2.** The Vertex AI region is correctly set to `europe-west2` for UK data residency, but the Cloud SQL instance (`tood-os-instance`) is provisioned in `us-east4`. This is a non-ideal configuration for UK data residency and should be reviewed before production.
- **No malware scanner configured.** File uploads are parsed and stored, but no malware scanning step runs. The upload response includes an explicit note about this. A scanner should be configured before production.
- **Cloud SQL automated backups not enabled.** The instance uses `db-f1-micro` and automated backups are not confirmed enabled.
- **Stripe webhook secret is a placeholder.** Billing events from Stripe will not be processed until a real webhook secret is configured.

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| API | FastAPI (Python) | ≥0.115 |
| Runtime | Python | 3.12 |
| Frontend | Next.js | 16.4.0 |
| UI runtime | React | 19.3.0 |
| Database | PostgreSQL 16 with pgvector | pg16 |
| Containerisation | Docker / Docker Compose | - |
| CI/CD | GitHub Actions | - |
| Deployment | Google Cloud Run | europe-west2 |
| Object storage | Local disk (development); Cloud Storage interface available | - |
| Payments | Stripe | ≥10.0 |

---

## AI Services Used

- **Gemini 2.5 Pro via Vertex AI** — primary drafting model. Configured for GCP project `tood-os`, region `europe-west2`. A residency guard (`app/ai_gateway/residency.py`) enforces that AI calls are only made to regions in the `AI_ALLOWED_REGIONS` list, which is pre-configured to include only European regions.
- **Gemini 2.0 Flash** — automatic fallback if Gemini 2.5 Pro fails.
- **Template provider** — local fallback with no external AI call. Active by default in development. Writes drafts by quoting evidence verbatim. No data leaves the machine.

All AI calls are routed exclusively through `app/ai_gateway`. Business code never imports a vendor AI SDK directly.

---

*Document prepared from actual codebase inspection. Verified: 44 tests passing, 17/17 install checks, ruff clean, Next.js build successful.*
