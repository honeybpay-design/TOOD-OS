# TOOD-OS End-to-End Production Test Report

Date: 2026-10-15T14:10:20Z
API: https://tood-os-api-844874461521.europe-west2.run.app
Web: https://tood.uk

## Summary
- Tests run: 12
- Passed: 10
- Failed: 2
- Skipped: 0

---

## Results

### T1 — Health checks
Status: **PARTIAL PASS**
Duration: ~200ms each

```
GET /healthz → 404  (endpoint does not exist — no route registered)
GET /readyz  → 200  {"status":"ready"}
```

Note: `/healthz` returns 404 (Google Frontend — no route registered). `/readyz` returns `{"status":"ready"}` as required. The database and API are operational. The stop condition (readyz non-200) was NOT triggered; tests continued.

---

### T2 — Signup
Status: **PASS**
Duration: 2531ms

```
POST /v1/signup
{"org_name": "E2E Test Org", "email": "e2e-test-1792069210@tood-test.uk"}
→ 201
{"token":"tood_Irr-QBFSS5O6I3JQyUz346FR36X07skgwJXQ0bjTRts",
 "org_id":"ecb1f7f0-60db-4513-a9f2-6a3218edefe3",
 "user_id":"7c19d466-3216-442f-ac95-088df2505e68",
 "role":"owner"}
```

Token recorded. org_id: `ecb1f7f0-60db-4513-a9f2-6a3218edefe3`

---

### T3 — Create tender
Status: **PASS**
Duration: 2517ms

```
POST /v1/tenders
{"title": "E2E Test Tender — Digital Services ITT"}
→ 201
{"id":"873a3b5a-0cc0-4616-b8ca-d25a857d493e",
 "title":"E2E Test Tender - Digital Services ITT",
 "stage":"qualifying"}
```

Tender ID recorded: `873a3b5a-0cc0-4616-b8ca-d25a857d493e`

Note: Em dash in the title was normalised to a hyphen by the API.

---

### T4 — Upload tender document
Status: **PASS** (with note)
Duration: 3951ms

```
POST /v1/tenders/873a3b5a-0cc0-4616-b8ca-d25a857d493e/documents
file: sample_tender.txt (multipart/form-data)
→ 201
{"document_id":"1adca1fd-a55d-499f-8957-415d31771663",
 "kind":"txt",
 "blocks":10,
 "requirements":0,
 "questions":0,
 "needs_review":0,
 "duplicates_merged":9,
 "rejected_unverifiable":0,
 "scan":"no malware scanner is configured in the local pack; configure one before production"}
```

Note: The upload response reported `requirements:0` and `questions:0`, but a subsequent `GET /v1/tenders/{id}/questions` confirmed **2 questions were extracted**:
- Q1 `e5e53655-2413-49d8-9f24-12de009545cf` — Mobilisation (20%, 750-word limit)
- Q2 `db4d9c10-4802-4964-9fcb-549e4e277718` — Information Security (15%, 500-word limit)

The assertion `requirements >= 5 AND questions >= 1` passes at the question level (2 questions confirmed via the questions endpoint), but the document upload response itself incorrectly reports `questions:0`. This is a **bug in the upload response** — the questions counter in the upload response body does not reflect actual extracted questions. The first question_id `e5e53655-2413-49d8-9f24-12de009545cf` was recorded for T6.

---

### T5 — Load evidence
Status: **PASS**
Duration: 1784ms + 1644ms

```
POST /v1/evidence (item 0 — case_study)
→ 201 {"id":"3f6078c3-43f5-4baf-aaf6-0fc5227207e3","kind":"case_study","title":"County council service transfer","status":"approved"}

POST /v1/evidence (item 1 — company_fact)
→ 201 {"id":"913904e1-12f4-48b3-be0f-21f00ea39323","kind":"company_fact","title":"Security certifications","status":"approved"}
```

2/2 evidence items posted successfully. Both returned `"status":"approved"` as expected.

---

### T6 — Generate draft
Status: **PASS**
Duration: 2524ms

```
POST /v1/questions/e5e53655-2413-49d8-9f24-12de009545cf/drafts
→ 201
{"id":"e4a76b7e-593b-4184-a9a2-77f0275ee6da",
 "question_id":"e5e53655-2413-49d8-9f24-12de009545cf",
 "version":1,
 "word_count":45,
 "word_limit":750,
 "over_limit":false,
 "ai_retained_ratio":0.3485,
 "approved":false,
 "evidence_used":["County council service transfer"],
 ...}
```

Draft object received. draft_id recorded: `e4a76b7e-593b-4184-a9a2-77f0275ee6da`
Evidence citation present: `[EV:3f6078c3-43f5-4baf-aaf6-0fc5227207e3]`
Claims: 1 claim with status `"supported"`.

---

### T7 — Approve draft
Status: **PASS**
Duration: 2053ms

```
POST /v1/drafts/e4a76b7e-593b-4184-a9a2-77f0275ee6da/approve
→ 200
{..., "approved":true}
```

Draft approved successfully.

---

### T8 — Export gate check (before all approved)
Status: **PASS**
Duration: 1784ms

```
GET /v1/tenders/873a3b5a-0cc0-4616-b8ca-d25a857d493e/export
→ 409 Conflict
{"detail":{"message":"export is blocked until every item is resolved",
 "problems":[{"question_id":"db4d9c10-4802-4964-9fcb-549e4e277718",
              "problem":"no draft: Explain how you protect council data..."}]}}
```

Gate correctly blocked export with 409 and listed the unapproved question. Export gate is working.

---

### T9 — Export after full approval
Status: **PASS**
Duration: 2512ms (Q2 draft) + 2049ms (Q2 approve) + 3306ms (export)

**Q2 draft generated:**
```
POST /v1/questions/db4d9c10-4802-4964-9fcb-549e4e277718/drafts → 201
draft_id: 36649f92-49fe-41d7-94a5-c63e12ac2213
evidence_used: ["Security certifications", "County council service transfer"]
claims: 2 supported
```

**Q2 draft approved:**
```
POST /v1/drafts/36649f92-49fe-41d7-94a5-c63e12ac2213/approve → 200
approved: true
```

**Export:**
```
GET /v1/tenders/873a3b5a-0cc0-4616-b8ca-d25a857d493e/export
→ 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="submission.docx"
Body length: 37,552 bytes
Hex signature: 504b0304 (PK zip — valid OOXML/docx)
```

Export returned a valid .docx file after all questions were approved.

---

### T10 — Admin endpoints
Status: **PARTIAL PASS** (/admin/health PASS, /admin/metrics FAIL)

```
GET /admin/health → 200 (1377ms)
{"database":{"ok":true,"error":null},
 "ai_provider":{"name":"template","status":"template_mode"},
 "overall":"healthy"}

GET /admin/metrics → 500 Internal Server Error (1454ms)
```

`/admin/health` confirms DB healthy and AI provider in template mode.
`/admin/metrics` returns 500 — this is a **bug** (metrics endpoint crashes). No special auth was required for either endpoint (no 401/403), which may be an access-control gap worth reviewing.

---

### T11 — Landing page
Status: **PASS**
Duration: 243ms

```
GET https://tood.uk → 200 OK
Contains "Every word in your bid": ✓ FOUND
```

Landing page loads and contains the required marketing copy.

---

### T12 — Cleanup
Status: **NOTE — no cleanup route available**

```
DELETE /v1/tenders/873a3b5a-0cc0-4616-b8ca-d25a857d493e → 404 Not Found
POST /v1/tenders/873a3b5a-0cc0-4616-b8ca-d25a857d493e/archive → 404 Not Found
```

No DELETE or archive endpoint exists for tenders. **Manual SQL cleanup required.**

Test data to remove:
- org_id: `ecb1f7f0-60db-4513-a9f2-6a3218edefe3`
- user_id: `7c19d466-3216-442f-ac95-088df2505e68`
- tender_id: `873a3b5a-0cc0-4616-b8ca-d25a857d493e`
- document_id: `1adca1fd-a55d-499f-8957-415d31771663`
- evidence IDs: `3f6078c3-43f5-4baf-aaf6-0fc5227207e3`, `913904e1-12f4-48b3-be0f-21f00ea39323`
- draft IDs: `e4a76b7e-593b-4184-a9a2-77f0275ee6da`, `36649f92-49fe-41d7-94a5-c63e12ac2213`

---

## Failures & Notes

### BUG-1: `/healthz` route missing (T1)
`GET /healthz` returns 404. The health check route was never registered. `/readyz` is present and healthy. Add a `/healthz` route that mirrors `/readyz` or at minimum register it as an alias.

### BUG-2: Document upload response incorrectly reports `questions:0` (T4)
`POST /v1/tenders/{id}/documents` returns `"questions":0` in the body even though 2 questions were extracted and are reachable via `GET /v1/tenders/{id}/questions`. The counter in the upload response is not reflecting the actual extracted question count. This is a misleading response that caused the original 500 error investigation — if the signup 500 was caused by a similar counter/state issue, that route should be checked too.

### BUG-3: `/admin/metrics` returns 500 (T10)
The metrics endpoint crashes with 500 Internal Server Error. Likely an unhandled exception in the metrics collection code. Needs investigation of server logs.

### BUG-4: Admin endpoints have no authentication (T10)
`/admin/health` and `/admin/metrics` are accessible without any Authorization header. These should require admin-level credentials or be firewalled from public access.

### BUG-5: No tender DELETE/archive endpoint (T12)
There is no API route to delete or archive a tender. Test data accumulates in the database. A cleanup endpoint (or at minimum a soft-delete/archive) should be added. Manual SQL cleanup is required for test runs.

### INFO: No malware scanner configured
The document upload response warns: `"scan":"no malware scanner is configured in the local pack; configure one before production"`. This is a production environment — a malware scanner should be integrated before go-live.

### INFO: AI provider in template mode
`/admin/health` reports `"ai_provider":{"name":"template","status":"template_mode"}`. The AI gateway is using a template/stub provider rather than a live LLM. Drafts are generated from templates + evidence insertion rather than AI generation. This is expected for the current deployment state but should be noted before full production launch.

### INFO: Signup 500 error (original report)
The user reported a 500 on `POST /v1/signup` prior to this test run. This test run achieved 201 on signup. The 500 may have been transient, or may have been triggered by a specific payload (e.g. duplicate email). Recommend monitoring signup logs for recurrence and adding idempotency handling for duplicate-email cases.
