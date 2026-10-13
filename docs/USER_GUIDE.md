# TOOD User Guide

Version: 0.2.0 | Date: 2026-10-13

*This guide is for bid managers, procurement officers, and bid writers using TOOD to prepare public-sector tender responses.*

---

## Getting Started

### 1. Sign up or sign in

**Email sign-up (available now):**

1. Go to the TOOD landing page and click **Start free trial**.
2. Choose a plan (Starter, Professional, or Enterprise).
3. Complete Stripe checkout to activate your subscription.
4. Once your workspace is created, you receive an API token to access the platform.

**Sign in with Google (UNVERIFIED — pending production deployment):**

1. Go to `/login` and click **Sign in with Google**.
2. Authenticate with your Google account.
3. You are redirected back to the TOOD dashboard.

> **Note:** Google OAuth is implemented in the codebase but has not been tested against the live production environment. It requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and migration 0006 to be applied to the production database.

### 2. Creating a workspace (organisation)

When you sign up, a workspace is created automatically for your organisation. The first user receives the `owner` role. Additional users can be added by an admin.

**Roles available:**
- `viewer` — read-only access
- `contributor` — can add evidence, generate drafts, and edit drafts
- `bid_manager` — can approve evidence, approve drafts, acknowledge claims, and export
- `admin` — platform administration
- `owner` — full control

---

## Uploading a Tender Document

### Supported formats

- PDF (`.pdf`)
- Word document (`.docx`)
- Plain text (`.txt`)
- Maximum file size: **20 MB**

### Steps

1. Create a tender: `POST /v1/tenders` with a title (2–300 characters). The tender appears in your tender list.
2. Upload the document to the tender: use the upload interface to attach the file.
3. TOOD reads the file, identifies its format by inspecting content (not the file extension), and parses it into blocks.
4. Requirement extraction runs automatically after parsing.

### What happens after upload

- The file is parsed into page blocks.
- Each block is hashed (SHA-256) and stored.
- Requirements are extracted from the blocks (see next section).
- The file is stored on disk (local development) or cloud storage (production).
- The upload response includes a count of requirements found, questions created, and any items flagged for review.
- A note is included if no malware scanner is configured (expected in development; configure one before production).

---

## Reviewing Extracted Requirements

### What verbatim extraction means

TOOD extracts requirement text **word-for-word** from the tender document. The extracted text is not paraphrased or summarised. Each requirement includes:

- The exact wording from the document
- The source document, page number, and section reference
- A word limit (if stated in the document)
- A due date (if stated)
- A weighting (if stated)

### Confidence scores

Each extracted requirement has a confidence score (0–1). Requirements with a confidence score below 0.7 are given the status `requires_review`. You should manually review these before drafting to confirm they are real requirements and not extracted noise.

Requirements with a score of 0.7 or above are automatically assigned the status `extracted` and are ready for drafting.

---

## Managing Your Evidence Library

The evidence library is the source of truth for all AI-generated drafts. Nothing outside this library can be cited in a draft.

### Adding evidence items

1. Navigate to the evidence section.
2. Add a new item with:
   - **Kind** — one of: `case_study`, `policy`, `cv`, `method`, `financial`, `company_fact`
   - **Title** — a short descriptive name (2–200 characters)
   - **Body** — the full text of the evidence (10–20,000 characters)
3. Only users with the `contributor` role or above can add evidence.

### Approving evidence

Evidence items start in `draft` status and cannot be used for AI drafting until they are approved.

- A user with the `bid_manager` role (or above) must approve each item: `POST /v1/evidence/{evidence_id}/approve`.
- Once approved, the item becomes searchable by the drafting engine.

> Only approved evidence is used when generating drafts. Unapproved evidence items are ignored.

### Evidence kinds

| Kind | Use case |
|---|---|
| `case_study` | Past contracts, delivery examples, references |
| `policy` | Internal policies, procedures, accreditations |
| `cv` | Staff CVs and competency records |
| `method` | Methodologies, approaches, frameworks |
| `financial` | Financial statements, turnover figures |
| `company_fact` | General company information, certifications |

---

## Drafting Answers

### Generating a draft (AI)

1. Open a question in your tender.
2. Click **Generate draft** (or `POST /v1/questions/{question_id}/drafts`).
3. TOOD searches the approved evidence library for items relevant to the question, then drafts a response using the configured AI provider (Gemini 2.5 Pro in production; template provider in development).
4. The draft is saved with version number 1.

If no approved evidence matches the question, the draft will note this explicitly. Add relevant evidence and regenerate.

### Editing a draft

1. Open the latest draft for a question.
2. Edit the text.
3. Submit the edit (`PATCH /v1/drafts/{draft_id}`).
4. A new version is saved. The edit spawns a new entry in the revision chain.

You can only edit the **latest** version of a draft. Editing an older version returns a 409 error.

### Understanding claim verification

After every draft (generated or edited), TOOD inspects the text for factual claims — numbers, certifications, statistics, named clients. Each claim is checked against the evidence library:

- **Supported** — the claim matches an approved evidence item.
- **Unsupported** — no evidence was found for this claim.

Unsupported claims block export until they are resolved.

### Acknowledging flagged claims

If a claim is flagged as unsupported but you have good reason to include it (for example, the evidence is in a format TOOD cannot read), a bid manager can acknowledge the claim: `POST /v1/claims/{claim_id}/acknowledge`.

Acknowledging a claim records your named decision in the audit log. It does not mean the claim is verified — it means a named human has consciously decided to include it.

---

## Approving and Exporting

### Named approval requirement

Before a draft can be included in an export, a bid manager must explicitly approve it:

`POST /v1/drafts/{draft_id}/approve`

The approval is tied to the specific revision hash of that draft. If the draft is edited after approval, it must be approved again.

### Export gate — what blocks export

`GET /v1/tenders/{tender_id}/readiness` shows you what is blocking export. A tender is ready to export only when:

1. Every question has at least one draft.
2. Every latest draft is approved by a named bid manager.
3. No latest draft has unacknowledged unsupported claims.
4. No latest draft exceeds the question's word limit.

If any condition is not met, the readiness check lists each blocking problem.

### Downloading the Word submission pack

When the tender passes the readiness check:

`GET /v1/tenders/{tender_id}/export`

This returns a `.docx` file containing all approved answers. The export file's SHA-256 hash and the revision hash of each answer are recorded in the database for future audit.

---

## Admin Dashboard (Professional/Enterprise)

Users with the `admin` role have access to platform metrics:

- `GET /admin/metrics` — MRR, active subscriptions, total organisations, 30-day churn rate
- `GET /admin/tenants` — list of all organisations with tender and user counts
- `GET /admin/health` — system health check (database, AI provider)
- `GET /admin/report` — daily summary report

---

## Subscription and Billing

### Plans and limits

| Plan | Price | Tenders | Users | AI drafting |
|---|---|---|---|---|
| Starter | £99/mo | 3 | 2 | Template (no external AI) |
| Professional | £299/mo | 20 | 10 | Gemini 2.5 Pro |
| Enterprise | £799/mo | Unlimited | Unlimited | Gemini 2.5 Pro |

### Upgrading

To upgrade your plan:

1. Call `POST /v1/billing/checkout` with your chosen plan and return URLs.
2. You are redirected to a Stripe Checkout page.
3. Complete payment. Your plan updates automatically via Stripe webhook.

> **Note:** Stripe webhook processing requires `STRIPE_WEBHOOK_SECRET` to be configured. If this is a placeholder value, webhook events will not be processed automatically.

---

## Troubleshooting

### Draft has no evidence cited

The question's keywords did not match any approved evidence item in full-text search. Try:
- Adding more evidence items relevant to the question topic.
- Ensuring evidence items are approved (not in `draft` status).
- Regenerating the draft after adding evidence.

### Export is blocked

Run `GET /v1/tenders/{tender_id}/readiness` to see the exact list of problems. Common causes:
- A question has no draft — generate one.
- A draft has not been approved — ask a bid manager to approve it.
- A draft has unsupported claims — acknowledge or remove them.
- A draft exceeds the word limit — edit it to reduce the word count.

### Upload fails

- **413 error** — file is larger than 20 MB. Compress or split the document.
- **415 error** — file format not recognised or file is disguised (TOOD checks file content, not extension). Try converting to a standard PDF or DOCX.
- **422 error** — file could not be read (possibly password-protected or corrupted). Remove document protection and retry.

---

## Support

Contact: **hello@tood.uk**

> **Note:** The domain `tood.uk` is not yet live as of v0.2.0. DNS configuration is pending.
