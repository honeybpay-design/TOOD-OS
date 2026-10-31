"""HTTP API (blueprint section 20). Every customer query runs inside a tenant transaction."""

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg
from fastapi import APIRouter, Depends, File, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.ai_gateway.provider import get_provider
from app.core.audit_export import (
    EXPORT_SCHEMA,
    AuditExportBlocked,
    artifact_snapshot,
    assurance_headers,
    ensure_export_allowed,
)
from app.core.audit_models import AuditLogResponse
from app.core.audit_reader import read_audit_snapshot
from app.core.audit_v2 import GenerationAudit
from app.core.auth import Ctx, authenticate, create_account
from app.core.config import settings
from app.core.operations import business_operation
from app.core.tenant import tenant_connection, tenant_snapshot_connection
from app.provenance.hashchain import Revision, compute_hash, verify_chain
from app.services import billing as billing_svc
from app.services import drafting, parsing, requirements
from app.services.export import build_docx
from app.services.storage import StorageError, get_store

router = APIRouter(prefix="/v1")
EVIDENCE_KINDS = ("case_study", "policy", "cv", "method", "financial", "company_fact")


@contextmanager
def db(ctx: Ctx):
    with tenant_connection(ctx.org_id, dict_rows=True) as conn:
        # Initial cutover must wait for every mediated business/read transaction.
        # No permission-error fallback or per-tenant illusion of global grants.
        conn.execute("SELECT audit_v2.locked_version()")
        yield conn


def uid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(404, "not found") from exc


# ---------- accounts ----------
class SignupIn(BaseModel):
    org_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    if not settings.allow_signup:
        raise HTTPException(403, "sign-up is disabled in this environment")
    return create_account(body.org_name.strip(), body.email.strip(), audit_creation=True)


@router.get("/me")
def me(ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        org = conn.execute("SELECT id, name FROM organisations").fetchone()
        user = conn.execute("SELECT id, email FROM users WHERE id = %s", (ctx.user_id,)).fetchone()
    return {"org": org, "user": user, "role": ctx.role, "ai_provider": settings.ai_provider}


# ---------- tenders, documents, requirements ----------
class TenderIn(BaseModel):
    title: str = Field(min_length=2, max_length=300)


@router.post("/tenders", status_code=201)
def create_tender(
    body: TenderIn,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("bid_manager")
    with db(ctx) as conn:
        with business_operation(conn, ctx, "tender.created", {"title": body.title.strip()}, idempotency_key) as op:
            if op.replayed:
                row = conn.execute(
                    "SELECT id, title, stage FROM tenders WHERE id = %s", (op.reference["id"],)
                ).fetchone()
                if not row:
                    raise HTTPException(409, "committed tender is no longer available")
                return row
            row = conn.execute(
                "INSERT INTO tenders (org_id, title) VALUES (%s, %s) RETURNING id, title, stage",
                (ctx.org_id, body.title.strip()),
            ).fetchone()
            op.finish({"kind": "tender", "id": str(row["id"])}, target=row["id"])
            return row


@router.get("/tenders")
def list_tenders(ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        return conn.execute(
            "SELECT t.id, t.title, t.stage, "
            "(SELECT count(*) FROM requirements r WHERE r.tender_id = t.id) AS requirements, "
            "(SELECT count(*) FROM questions q WHERE q.tender_id = t.id) AS questions "
            "FROM tenders t ORDER BY t.created_at DESC"
        ).fetchall()


@router.post("/tenders/{tender_id}/documents", status_code=201)
async def upload_document(
    tender_id: str,
    file: UploadFile = File(...),
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("bid_manager")
    tid = uid(tender_id)
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"file is larger than {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "empty file")
    kind = parsing.sniff(data)  # the content decides, never the file name or the declared type
    if kind is None:
        raise HTTPException(415, "unsupported or disguised file: only PDF, DOCX and plain text are accepted")
    try:
        blocks = parsing.parse(data, kind)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, "the file could not be read; it may be damaged or protected") from exc
    if not blocks:
        raise HTTPException(
            422, "no usable text was found; provide a text-readable document or apply OCR before uploading"
        )
    name = re.sub(r"[^\w.\- ]", "_", (file.filename or "document"))[:200]
    with db(ctx) as conn:
        if not conn.execute("SELECT 1 FROM tenders WHERE id = %s", (tid,)).fetchone():
            raise HTTPException(404, "tender not found")
        with business_operation(
            conn,
            ctx,
            "document.uploaded",
            {
                "tender_id": str(tid),
                "file_sha256": hashlib.sha256(data).hexdigest(),
                "file_size": len(data),
                "file_name": name,
                "format": kind,
            },
            idempotency_key,
        ) as op:
            if op.replayed:
                original = conn.execute(
                    "SELECT storage_key, sha256 FROM documents WHERE id = %s", (op.reference["id"],)
                ).fetchone()
                if not original:
                    raise HTTPException(409, "committed document is no longer available")
                try:
                    stored = await run_in_threadpool(
                        lambda: get_store().get(
                            original["storage_key"], org_id=ctx.org_id, expected_sha256=original["sha256"]
                        )
                    )
                except (StorageError, OSError, ValueError) as exc:
                    raise HTTPException(503, "the committed original cannot be verified") from exc
                if stored != data:
                    raise HTTPException(409, "idempotency key conflicts with original file bytes")
                return {
                    "document_id": op.reference["id"],
                    "kind": op.reference["format"],
                    **op.reference["counts"],
                    "scan": "no malware scanner is configured in the local pack; configure one before production",
                }
            if not conn.execute("SELECT id FROM tenders WHERE id = %s FOR UPDATE", (tid,)).fetchone():
                raise HTTPException(404, "tender not found")
            doc_id = op.new_id("document")
            try:
                store_key = await run_in_threadpool(lambda: get_store().put(ctx.org_id, doc_id, data))
            except (StorageError, OSError) as exc:
                raise HTTPException(503, "the document could not be stored safely; please try again") from exc
            conn.execute(
                "INSERT INTO documents (id, org_id, tender_id, file_name, storage_key, mime_type, sha256, parse_status, parser_version)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,'parsed',%s)",
                (
                    doc_id,
                    ctx.org_id,
                    tid,
                    name,
                    store_key,
                    kind,
                    hashlib.sha256(data).hexdigest(),
                    "rules-1+" + requirements.VERBATIM_VERSION,
                ),
            )
            for b in blocks:
                row = conn.execute(
                    "INSERT INTO doc_blocks (org_id, document_id, page, bbox, kind, text, section_path, block_hash)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (
                        ctx.org_id,
                        doc_id,
                        b["page"],
                        json.dumps(b["bbox"]) if b["bbox"] else None,
                        b["kind"],
                        b["text"],
                        b["section_path"],
                        hashlib.sha256(b["text"].encode()).hexdigest(),
                    ),
                ).fetchone()
                b["id"] = row["id"]
            existing = {
                r["text_verbatim"]
                for r in conn.execute("SELECT text_verbatim FROM requirements WHERE tender_id = %s", (tid,))
            }
            found = rejected = duplicates = review = questions = 0
            question_blocks: set = set()
            # Freeze trusted parsed source before invoking a candidate proposer.
            trusted_sources = {b["id"]: (b["text"], hashlib.sha256(b["text"].encode()).hexdigest()) for b in blocks}
            for c in requirements.extract_candidates(blocks):
                source = trusted_sources.get(c.get("block_id"))
                if source is None or not requirements.verify_verbatim(
                    c["text_verbatim"], source[0], expected_block_hash=source[1]
                ):
                    rejected += 1  # wording not found in its source block: discard (V2)
                    continue
                if c["text_verbatim"] in existing:
                    duplicates += 1
                    continue
                existing.add(c["text_verbatim"])
                req = conn.execute(
                    "INSERT INTO requirements (org_id, tender_id, type, title, text_verbatim, weighting, word_limit, due_at,"
                    " source_block_id, confidence, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (
                        ctx.org_id,
                        tid,
                        c["type"],
                        c["title"],
                        c["text_verbatim"],
                        c["weighting"],
                        c["word_limit"],
                        c["due_at"],
                        c["block_id"],
                        c["confidence"],
                        "requires_review" if c["confidence"] < 0.7 else "extracted",
                    ),
                ).fetchone()
                found += 1
                review += 1 if c["confidence"] < 0.7 else 0
                if c["type"] == "scored_question" and c["block_id"] not in question_blocks:
                    question_blocks.add(c["block_id"])
                    conn.execute(
                        "INSERT INTO questions (org_id, tender_id, requirement_id, prompt, weighting, word_limit)"
                        " VALUES (%s,%s,%s,%s,%s,%s)",
                        (ctx.org_id, tid, req["id"], c["prompt"], c["weighting"], c["word_limit"]),
                    )
                    questions += 1
            op.finish(
                {
                    "kind": "document",
                    "id": str(doc_id),
                    "format": kind,
                    "counts": {
                        "blocks": len(blocks),
                        "requirements": found,
                        "questions": questions,
                        "needs_review": review,
                        "duplicates_merged": duplicates,
                        "rejected_unverifiable": rejected,
                    },
                },
                target=doc_id,
            )
    return {
        "document_id": str(doc_id),
        "kind": kind,
        "blocks": len(blocks),
        "requirements": found,
        "questions": questions,
        "needs_review": review,
        "duplicates_merged": duplicates,
        "rejected_unverifiable": rejected,
        "scan": "no malware scanner is configured in the local pack; configure one before production",
    }


@router.get("/tenders/{tender_id}/requirements")
def list_requirements(tender_id: str, ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        return conn.execute(
            "SELECT r.id, r.type, r.title, r.text_verbatim, r.weighting, r.word_limit, r.due_at, r.confidence, r.status,"
            " b.page, d.file_name FROM requirements r JOIN doc_blocks b ON b.id = r.source_block_id"
            " JOIN documents d ON d.id = b.document_id WHERE r.tender_id = %s ORDER BY r.created_at",
            (uid(tender_id),),
        ).fetchall()


@router.get("/tenders/{tender_id}/questions")
def list_questions(tender_id: str, ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        return conn.execute(
            "SELECT q.id, q.prompt, q.weighting, q.word_limit,"
            " (SELECT d.id FROM drafts d WHERE d.question_id = q.id ORDER BY d.version DESC LIMIT 1) AS latest_draft"
            " FROM questions q WHERE q.tender_id = %s ORDER BY q.created_at",
            (uid(tender_id),),
        ).fetchall()


# ---------- evidence ----------
class EvidenceIn(BaseModel):
    kind: str
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=10, max_length=20000)
    approved: bool = False


def _chunks(body: str) -> list[str]:
    out, cur = [], ""
    for s in re.split(r"(?<=[.!?])\s+", body.strip()):
        if len(cur) + len(s) > 400 and cur:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    return out + ([cur] if cur else [])


@router.post("/evidence", status_code=201)
def add_evidence(
    body: EvidenceIn,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("contributor")
    if body.kind not in EVIDENCE_KINDS:
        raise HTTPException(422, f"kind must be one of {', '.join(EVIDENCE_KINDS)}")
    if body.approved:
        ctx.require("bid_manager")  # only a bid manager or above can approve evidence
    with db(ctx) as conn:
        with business_operation(
            conn,
            ctx,
            "evidence.created",
            {
                "kind": body.kind,
                "title": body.title.strip(),
                "body": body.body,
                "approved": body.approved,
            },
            idempotency_key,
        ) as op:
            if op.replayed:
                row = conn.execute(
                    "SELECT id, kind, title, status FROM evidence_items WHERE id = %s", (op.reference["id"],)
                ).fetchone()
                if not row:
                    raise HTTPException(409, "committed evidence is no longer available")
                return row
            row = conn.execute(
                "INSERT INTO evidence_items (org_id, kind, title, body, owner_id, status) VALUES (%s,%s,%s,%s,%s,%s)"
                " RETURNING id, kind, title, status",
                (
                    ctx.org_id,
                    body.kind,
                    body.title.strip(),
                    body.body.strip(),
                    ctx.user_id,
                    "approved" if body.approved else "draft",
                ),
            ).fetchone()
            for i, chunk in enumerate(_chunks(body.body)):
                conn.execute(
                    "INSERT INTO evidence_chunks (org_id, evidence_id, chunk_index, content_text, embedding_model)"
                    " VALUES (%s,%s,%s,%s,'none')",
                    (ctx.org_id, row["id"], i, chunk),
                )
            op.finish({"kind": "evidence", "id": str(row["id"])}, target=row["id"])
    return row


@router.post("/evidence/{evidence_id}/approve")
def approve_evidence(
    evidence_id: str,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("bid_manager")
    eid = uid(evidence_id)
    with db(ctx) as conn:
        if not conn.execute("SELECT 1 FROM evidence_items WHERE id = %s", (eid,)).fetchone():
            raise HTTPException(404, "evidence not found")
        with business_operation(conn, ctx, "evidence.approved", {"evidence_id": str(eid)}, idempotency_key) as op:
            if op.replayed:
                return conn.execute(
                    "SELECT id, title, status FROM evidence_items WHERE id = %s", (op.reference["id"],)
                ).fetchone()
            row = conn.execute(
                "UPDATE evidence_items SET status = 'approved' WHERE id = %s RETURNING id, title, status", (eid,)
            ).fetchone()
            op.finish({"kind": "evidence", "id": str(row["id"])}, target=row["id"])
            return row


@router.get("/evidence")
def list_evidence(ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        return conn.execute(
            "SELECT id, kind, title, status, left(body, 200) AS preview FROM evidence_items ORDER BY created_at DESC"
        ).fetchall()


# ---------- drafting ----------
def _draft_view(conn, draft) -> dict:
    content = draft["content"]
    claims = conn.execute(
        "SELECT id, sentence_span, evidence_ids, status FROM draft_claims WHERE draft_id = %s ORDER BY id",
        (draft["id"],),
    ).fetchall()
    q = conn.execute("SELECT word_limit FROM questions WHERE id = %s", (draft["question_id"],)).fetchone()
    approved = conn.execute("SELECT a.approved_at FROM approvals a WHERE a.draft_id = %s", (draft["id"],)).fetchone()
    return {
        "id": draft["id"],
        "question_id": draft["question_id"],
        "version": draft["version"],
        "text": content["text"],
        "spans": content["spans"],
        "model_id": content["model_id"],
        "word_count": draft["word_count"],
        "word_limit": q["word_limit"],
        "over_limit": bool(q["word_limit"] and draft["word_count"] > q["word_limit"]),
        "ai_retained_ratio": drafting.ai_retained_ratio(content["spans"]),
        "claims": claims,
        "approved": bool(approved),
    }


def _evidence_map(conn) -> dict:
    return {str(r["id"]): r for r in conn.execute("SELECT id, title, body, status FROM evidence_items")}


@dataclass(frozen=True)
class SavedVersion:
    draft: dict
    revision_id: uuid.UUID
    revision_hash: str


def _save_version(conn, ctx, question_id, text, spans, model_id, prompt_version, thread_id, version) -> SavedVersion:
    content = {"text": text, "spans": spans, "model_id": model_id, "prompt_version": prompt_version}
    draft = conn.execute(
        "INSERT INTO drafts (org_id, question_id, version, content, word_count) VALUES (%s,%s,%s,%s,%s) RETURNING *",
        (ctx.org_id, question_id, version, json.dumps(content), drafting.word_count(text)),
    ).fetchone()
    thread = thread_id or draft["id"]
    content["thread_id"] = str(thread)
    conn.execute("UPDATE drafts SET content = %s WHERE id = %s", (json.dumps(content), draft["id"]))
    draft["content"] = content
    for claim in drafting.verify_claims(text, _evidence_map(conn)):
        conn.execute(
            "INSERT INTO draft_claims (org_id, draft_id, sentence_span, evidence_ids, status) VALUES (%s,%s,%s,%s,%s)",
            (
                ctx.org_id,
                draft["id"],
                claim["sentence_span"],
                [uuid.UUID(i) for i in claim["evidence_ids"]],
                claim["status"],
            ),
        )
    prev = conn.execute(
        "SELECT hash FROM revisions WHERE draft_id = %s ORDER BY seq DESC LIMIT 1", (thread,)
    ).fetchone()
    seq = version
    snapshot = {k: content[k] for k in ("text", "spans", "model_id", "prompt_version")}
    h = compute_hash(snapshot, {"actor": str(ctx.user_id), "seq": seq}, prev["hash"] if prev else None)
    revision = conn.execute(
        "INSERT INTO revisions (org_id, draft_id, seq, prev_hash, hash, content_snapshot, origin_spans, actor_id)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (
            ctx.org_id,
            thread,
            seq,
            prev["hash"] if prev else None,
            h,
            json.dumps(snapshot),
            json.dumps(spans),
            ctx.user_id,
        ),
    ).fetchone()
    return SavedVersion(draft=draft, revision_id=revision["id"], revision_hash=h)


STOP = {
    "your",
    "that",
    "this",
    "with",
    "from",
    "must",
    "should",
    "shall",
    "will",
    "have",
    "including",
    "response",
    "question",
    "carries",
    "weighting",
    "words",
    "exceed",
    "describe",
    "explain",
    "provide",
    "their",
    "they",
    "how",
    "the",
    "and",
    "for",
    "are",
    "any",
    "all",
    "can",
    "into",
    "each",
    "than",
    "also",
    "such",
    "which",
}


def _query_terms(prompt: str) -> str:
    """OR-query from the question's meaningful words (plain AND matching would find almost nothing)."""
    words = [w for w in re.findall(r"[a-z]{4,}", prompt.lower()) if w not in STOP]
    return " | ".join(dict.fromkeys(words))[:400]


@router.post("/questions/{question_id}/drafts", status_code=201)
def generate_draft(
    question_id: str,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("contributor")
    qid = uid(question_id)
    with db(ctx) as conn:
        q = conn.execute("SELECT id, prompt, word_limit FROM questions WHERE id = %s", (qid,)).fetchone()
        if not q:
            raise HTTPException(404, "question not found")
        with business_operation(conn, ctx, "draft.generated", {"question_id": str(qid)}, idempotency_key) as op:
            if op.replayed:
                draft = conn.execute("SELECT * FROM drafts WHERE id = %s", (op.reference["id"],)).fetchone()
                if not draft:
                    raise HTTPException(409, "committed draft is no longer available")
                view = _draft_view(conn, draft)
                ids = op.reference["evidence_ids"]
                titles = {
                    str(r["id"]): r["title"]
                    for r in conn.execute("SELECT id, title FROM evidence_items WHERE id = ANY(%s::uuid[])", (ids,))
                }
                view["evidence_used"] = [titles[i] for i in ids if i in titles]
                view["note"] = (
                    None if ids else "No approved evidence matched this question; add evidence and generate again."
                )
                return view
            q = conn.execute("SELECT id, prompt, word_limit FROM questions WHERE id = %s FOR UPDATE", (qid,)).fetchone()
            if not q:
                raise HTTPException(404, "question not found")
            provider = get_provider()
            terms = _query_terms(q["prompt"])
            evidence = (
                conn.execute(
                    "SELECT e.id, e.title, e.body, max(ts_rank(c.tsv, to_tsquery('english', %s))) AS rank"
                    " FROM evidence_chunks c JOIN evidence_items e ON e.id = c.evidence_id"
                    " WHERE e.status = 'approved' AND c.tsv @@ to_tsquery('english', %s)"
                    " GROUP BY e.id, e.title, e.body ORDER BY rank DESC LIMIT 3",
                    (terms, terms),
                ).fetchall()
                if terms
                else []
            )
            generation = provider.generate(
                q["prompt"], [{"id": str(e["id"]), "body": e["body"]} for e in evidence], q["word_limit"]
            )
            text, spans = drafting.segments_to_text(generation.segments)
            last = conn.execute(
                "SELECT version, content FROM drafts WHERE question_id = %s ORDER BY version DESC LIMIT 1", (qid,)
            ).fetchone()
            thread = uuid.UUID(last["content"]["thread_id"]) if last else None
            provider.validate_result(generation)
            saved = _save_version(
                conn,
                ctx,
                qid,
                text,
                spans,
                generation.model_id,
                generation.prompt_version,
                thread,
                (last["version"] + 1) if last else 1,
            )
            draft = saved.draft
            payload = None
            if op.mode == 2:
                payload = GenerationAudit(
                    draft["id"],
                    qid,
                    saved.revision_id,
                    bytes.fromhex(saved.revision_hash),
                    generation.requested_model_id,
                    generation.model_id,
                    generation.prompt_version,
                    bytes.fromhex(generation.admission_digest) if generation.admission_digest is not None else None,
                ).payload()
            op.finish(
                {"kind": "draft", "id": str(draft["id"]), "evidence_ids": [str(e["id"]) for e in evidence]},
                target=draft["id"],
                payload=payload,
                payload_schema="tood.draft-generated.v1",
            )
            view = _draft_view(conn, draft)
    view["evidence_used"] = [e["title"] for e in evidence]
    view["note"] = None if evidence else "No approved evidence matched this question; add evidence and generate again."
    return view


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str, ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        draft = conn.execute("SELECT * FROM drafts WHERE id = %s", (uid(draft_id),)).fetchone()
        if not draft:
            raise HTTPException(404, "draft not found")
        return _draft_view(conn, draft)


class DraftEdit(BaseModel):
    text: str = Field(min_length=1, max_length=40000)


@router.patch("/drafts/{draft_id}", status_code=201)
def edit_draft(
    draft_id: str,
    body: DraftEdit,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("contributor")
    did = uid(draft_id)
    with db(ctx) as conn:
        old = conn.execute("SELECT * FROM drafts WHERE id = %s", (did,)).fetchone()
        if not old:
            raise HTTPException(404, "draft not found")
        with business_operation(
            conn, ctx, "draft.edited", {"draft_id": str(did), "text": body.text}, idempotency_key
        ) as op:
            if op.replayed:
                row = conn.execute("SELECT * FROM drafts WHERE id = %s", (op.reference["id"],)).fetchone()
                if not row:
                    raise HTTPException(409, "committed draft is no longer available")
                return _draft_view(conn, row)
            conn.execute("SELECT id FROM questions WHERE id = %s FOR UPDATE", (old["question_id"],)).fetchone()
            latest = conn.execute(
                "SELECT max(version) AS v FROM drafts WHERE question_id = %s", (old["question_id"],)
            ).fetchone()
            if old["version"] != latest["v"]:
                raise HTTPException(409, "this is not the latest version; edit the latest draft")
            spans = drafting.respan(old["content"]["text"], old["content"]["spans"], body.text)
            saved = _save_version(
                conn,
                ctx,
                old["question_id"],
                body.text,
                spans,
                old["content"]["model_id"],
                old["content"]["prompt_version"],
                uuid.UUID(old["content"]["thread_id"]),
                old["version"] + 1,
            )
            draft = saved.draft
            payload = None
            if op.mode == 2:
                source = conn.execute(
                    "SELECT id, hash FROM revisions WHERE draft_id = %s AND seq = %s",
                    (uuid.UUID(old["content"]["thread_id"]), old["version"]),
                ).fetchone()
                if not source:
                    raise HTTPException(409, "source revision is unavailable")
                payload = {
                    "source": "human_edit",
                    "draft_id": str(draft["id"]),
                    "question_id": str(old["question_id"]),
                    "revision_id": str(saved.revision_id),
                    "revision_hash": saved.revision_hash,
                    "source_draft_id": str(old["id"]),
                    "source_revision_id": str(source["id"]),
                    "source_revision_hash": source["hash"],
                }
            op.finish(
                {"kind": "draft", "id": str(draft["id"])},
                target=draft["id"],
                payload=payload,
                payload_schema="tood.draft-edited.v1",
            )
            return _draft_view(conn, draft)


@router.post("/claims/{claim_id}/acknowledge")
def acknowledge_claim(
    claim_id: str,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("bid_manager")
    cid = uid(claim_id)
    with db(ctx) as conn:
        if not conn.execute("SELECT 1 FROM draft_claims WHERE id = %s", (cid,)).fetchone():
            raise HTTPException(404, "no unsupported claim with that id")
        with business_operation(conn, ctx, "claim.acknowledged", {"claim_id": str(cid)}, idempotency_key) as op:
            if op.replayed:
                return {"id": uuid.UUID(op.reference["id"]), "status": "acknowledged"}
            conn.execute("SELECT q.id FROM questions q JOIN drafts d ON d.question_id = q.id "
                "JOIN draft_claims c ON c.draft_id = d.id WHERE c.id = %s FOR UPDATE OF q", (cid,)).fetchone()
            row = conn.execute(
                "UPDATE draft_claims SET status = 'acknowledged', acknowledged_by = %s WHERE id = %s AND status = 'unsupported' RETURNING id, status",
                (ctx.user_id, cid),
            ).fetchone()
            if not row:
                raise HTTPException(404, "no unsupported claim with that id")
            op.finish({"kind": "claim", "id": str(row["id"])}, target=row["id"])
            return row


@router.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("bid_manager")  # a named person approves; the system never approves for them
    with db(ctx) as conn:
        draft = conn.execute("SELECT * FROM drafts WHERE id = %s", (uid(draft_id),)).fetchone()
        if not draft:
            raise HTTPException(404, "draft not found")
        with business_operation(conn, ctx, "draft.approved", {"draft_id": str(draft["id"])}, idempotency_key) as op:
            if op.replayed:
                return _draft_view(conn, draft)
            conn.execute("SELECT id FROM questions WHERE id = %s FOR UPDATE", (draft["question_id"],)).fetchone()
            latest = conn.execute(
                "SELECT max(version) AS v FROM drafts WHERE question_id = %s", (draft["question_id"],)
            ).fetchone()
            if draft["version"] != latest["v"]:
                raise HTTPException(409, "only the latest version can be approved")
            rev = conn.execute(
                "SELECT id FROM revisions WHERE draft_id = %s AND seq = %s",
                (uuid.UUID(draft["content"]["thread_id"]), draft["version"]),
            ).fetchone()
            conn.execute(
                "INSERT INTO approvals (org_id, draft_id, revision_id, approver_id) VALUES (%s,%s,%s,%s)"
                " ON CONFLICT DO NOTHING",
                (ctx.org_id, draft["id"], rev["id"], ctx.user_id),
            )
            op.finish({"kind": "draft", "id": str(draft["id"])}, target=draft["id"])
            return _draft_view(conn, draft)


@router.get("/drafts/{draft_id}/provenance")
def provenance(draft_id: str, ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        draft = conn.execute("SELECT * FROM drafts WHERE id = %s", (uid(draft_id),)).fetchone()
        if not draft:
            raise HTTPException(404, "draft not found")
        thread = uuid.UUID(draft["content"]["thread_id"])
        revs = conn.execute(
            "SELECT seq, prev_hash, hash, content_snapshot, actor_id FROM revisions WHERE draft_id = %s ORDER BY seq",
            (thread,),
        ).fetchall()
        chain = [
            Revision(r["content_snapshot"], {"actor": str(r["actor_id"]), "seq": r["seq"]}, r["prev_hash"], r["hash"])
            for r in revs
        ]
        ok, bad = verify_chain(chain)
        text, spans = draft["content"]["text"], draft["content"]["spans"]
        return {
            "draft_id": draft["id"],
            "version": draft["version"],
            "ai_retained_ratio": drafting.ai_retained_ratio(spans),
            "spans": [{"origin": o, "text": text[s:e]} for s, e, o in spans],
            "chain": {"ok": ok, "first_bad_revision": bad, "revisions": len(revs)},
        }


# ---------- readiness and export ----------
def _readiness(conn, tender_id) -> list[dict]:
    problems = []
    questions = conn.execute(
        "SELECT id, prompt, word_limit FROM questions WHERE tender_id = %s ORDER BY created_at", (tender_id,)
    ).fetchall()
    if not questions:
        return [{"question_id": None, "problem": "the tender has no questions to answer"}]
    for q in questions:
        d = conn.execute(
            "SELECT * FROM drafts WHERE question_id = %s ORDER BY version DESC LIMIT 1", (q["id"],)
        ).fetchone()
        label = q["prompt"][:70]
        if not d:
            problems.append({"question_id": q["id"], "problem": f"no draft: {label}"})
            continue
        unsupported = conn.execute(
            "SELECT count(*) AS n FROM draft_claims WHERE draft_id = %s AND status = 'unsupported'", (d["id"],)
        ).fetchone()["n"]
        if unsupported:
            problems.append({"question_id": q["id"], "problem": f"{unsupported} unsupported claim(s): {label}"})
        if q["word_limit"] and d["word_count"] > q["word_limit"]:
            problems.append({"question_id": q["id"], "problem": f"over the {q['word_limit']}-word limit: {label}"})
        if not conn.execute("SELECT 1 FROM approvals WHERE draft_id = %s", (d["id"],)).fetchone():
            problems.append({"question_id": q["id"], "problem": f"not approved by a named person: {label}"})
    return problems


@router.get("/tenders/{tender_id}/readiness")
def readiness(tender_id: str, ctx: Ctx = Depends(authenticate)):
    with db(ctx) as conn:
        problems = _readiness(conn, uid(tender_id))
    return {"ready": not problems, "problems": problems}


@router.get(
    "/tenders/{tender_id}/export", response_class=Response,
    responses={200: {
        "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
            "schema": {"type": "string", "format": "binary"}
        }},
        "headers": {name: {"schema": {"type": "string"}} for name in (
            "X-Export-SHA256", "Idempotency-Replayed", "X-Audit-Assurance-Schema", "X-Audit-Artifact-Snapshot",
            "X-Audit-Artifact-Sequence", "X-Audit-Assessment-Sequence", "X-Audit-Assessment-Status",
            "X-Audit-Checkpoint-State",
        )},
    }},
)
def export(
    tender_id: str,
    ctx: Ctx = Depends(authenticate),
    idempotency_key: uuid.UUID | None = Header(default=None, alias="Idempotency-Key"),
):
    ctx.require("bid_manager")
    tid = uid(tender_id)
    with db(ctx) as conn:
        tender = conn.execute("SELECT title FROM tenders WHERE id = %s", (tid,)).fetchone()
        if not tender:
            raise HTTPException(404, "tender not found")
        with business_operation(conn, ctx, "tender.exported", {"tender_id": str(tid)}, idempotency_key) as op:
            # Consistent ordering: operation, tender, then questions in UUID order.
            # FOR UPDATE also excludes FK-backed new question inserts during export.
            tender = conn.execute("SELECT title FROM tenders WHERE id = %s FOR UPDATE", (tid,)).fetchone()
            if not tender:
                raise HTTPException(404, "tender not found")
            conn.execute("SELECT id FROM questions WHERE tender_id = %s ORDER BY id FOR UPDATE", (tid,)).fetchall()
            problems = _readiness(conn, tid)
            if problems:  # the export gate (blueprint section 17)
                raise HTTPException(
                    409,
                    {
                        "message": "export is blocked until every item is resolved",
                        "problems": [
                            {"question_id": str(p["question_id"]) if p["question_id"] else None, "problem": p["problem"]}
                            for p in problems
                        ],
                    },
                )
            assessment = _export_assessment(ctx)
            if op.replayed:
                manifest = conn.execute(
                    "SELECT file_sha256 FROM export_manifests WHERE id = %s AND tender_id = %s",
                    (op.reference["id"], tid),
                ).fetchone()
                if not manifest or manifest["file_sha256"] != op.reference["sha256"]:
                    raise HTTPException(409, "committed export manifest is unavailable")
                try:
                    data = get_store().get(
                        op.reference["storage_key"], org_id=ctx.org_id, expected_sha256=manifest["file_sha256"]
                    )
                except (StorageError, OSError, ValueError) as exc:
                    raise HTTPException(503, "the committed export cannot be verified") from exc
                metadata = conn.execute(
                    "SELECT payload_schema,payload_bytes FROM audit_v2.events "
                    "WHERE org_id=%s AND operation_id=%s AND action='tender.exported' AND target=%s LIMIT 2",
                    (ctx.org_id, op.operation_id, str(tid)),
                ).fetchall()
                if len(metadata) != 1:
                    raise HTTPException(409, "the committed export audit reference is not unique")
                try:
                    recorded = artifact_snapshot(
                        json.loads(bytes(metadata[0]["payload_bytes"])), metadata[0]["payload_schema"],
                        op.reference, assessment,
                    )
                    if recorded is not None:
                        sequence = int(recorded.v2.sequence)
                        if sequence == 0:
                            expected_head = assessment.v2.genesis_hash
                        else:
                            position = conn.execute(
                                "SELECT hash FROM audit_v2.events WHERE org_id=%s AND epoch_id=%s AND tenant_sequence=%s",
                                (ctx.org_id, uuid.UUID(recorded.v2.epoch_id), sequence),
                            ).fetchone()
                            expected_head = bytes(position["hash"]).hex() if position else None
                        if expected_head != recorded.v2.head_hash:
                            raise AuditExportBlocked("export_snapshot_hash_mismatch")
                except (ValueError, TypeError, KeyError, OverflowError) as exc:
                    raise HTTPException(409, "the committed export audit snapshot cannot be verified") from exc
                return Response(
                    content=data,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={
                        "Content-Disposition": 'attachment; filename="submission.docx"',
                        "X-Export-SHA256": manifest["file_sha256"],
                        "Idempotency-Replayed": "true",
                        **assurance_headers(recorded, assessment),
                    },
                )
            org = conn.execute("SELECT name FROM organisations").fetchone()["name"]
            evidence = _evidence_map(conn)
            answers, hashes = [], {}
            for q in conn.execute(
                "SELECT id, prompt FROM questions WHERE tender_id = %s ORDER BY created_at", (tid,)
            ).fetchall():
                d = conn.execute(
                    "SELECT * FROM drafts WHERE question_id = %s ORDER BY version DESC LIMIT 1", (q["id"],)
                ).fetchone()
                ap = conn.execute(
                    "SELECT approver_id, approved_at, revision_id FROM approvals WHERE draft_id = %s", (d["id"],)
                ).fetchone()
                who = conn.execute("SELECT email FROM users WHERE id = %s", (ap["approver_id"],)).fetchone()
                rev = conn.execute("SELECT hash FROM revisions WHERE id = %s", (ap["revision_id"],)).fetchone()
                ack = conn.execute(
                    "SELECT count(*) AS n FROM draft_claims WHERE draft_id = %s AND status = 'acknowledged'", (d["id"],)
                ).fetchone()["n"]
                cited = [
                    evidence[i]["title"]
                    for i in dict.fromkeys(drafting.EV_TAG.findall(d["content"]["text"].lower()))
                    if i in evidence
                ]
                answers.append(
                    {
                        "prompt": q["prompt"],
                        "text": d["content"]["text"],
                        "evidence_titles": cited,
                        "model_id": d["content"]["model_id"],
                        "ai_ratio": drafting.ai_retained_ratio(d["content"]["spans"]),
                        "approver": who["email"] if who else "unknown",
                        "approved_at": ap["approved_at"].strftime("%Y-%m-%d %H:%M"),
                        "acknowledged": ack,
                        "revision_hash": rev["hash"],
                    }
                )
                hashes[str(q["id"])] = rev["hash"]
            data = build_docx(tender["title"], org, answers, assessment.model_dump(mode="json"))
            digest = hashlib.sha256(data).hexdigest()
            export_id = op.new_id("export")
            reference = {"kind": "export", "id": str(export_id), "target_id": str(tid)}
            if op.mode == 2:
                try:
                    pointer = get_store().put(ctx.org_id, export_id, data)
                except (StorageError, OSError, ValueError) as exc:
                    raise HTTPException(503, "the immutable export could not be stored") from exc
                reference.update(sha256=digest, storage_key=pointer)
            conn.execute(
                "INSERT INTO export_manifests (id, org_id, tender_id, file_sha256, revision_hashes, created_by)"
                " VALUES (%s,%s,%s,%s,%s,%s)",
                (export_id, ctx.org_id, tid, digest, json.dumps(hashes), ctx.user_id),
            )
            op.finish(
                reference, target=tid,
                payload={"resource": reference, "audit_snapshot": assessment.model_dump(mode="json")},
                payload_schema=EXPORT_SCHEMA,
            )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'attachment; filename="submission.docx"', "X-Export-SHA256": digest,
            **assurance_headers(assessment, assessment),
        },
    )


def _audit_read(ctx: Ctx):
    try:
        with tenant_snapshot_connection(ctx.org_id) as conn:
            return read_audit_snapshot(conn, ctx.org_id)
    except (psycopg.Error, ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(503, "the audit snapshot cannot be verified") from exc


def _export_assessment(ctx: Ctx):
    assessment = _audit_read(ctx).assurance
    try:
        ensure_export_allowed(assessment)
    except AuditExportBlocked as exc:
        raise HTTPException(409, {"message": "export is blocked by audit integrity", "status": str(exc)}) from exc
    return assessment


# ---------- audit ----------
@router.get("/audit", response_model=AuditLogResponse)
def audit_log(ctx: Ctx = Depends(authenticate)):
    ctx.require("admin")
    return _audit_read(ctx)


# ---------- billing ----------


class CheckoutIn(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


@router.post("/billing/checkout")
def billing_checkout(body: CheckoutIn, ctx: Ctx = Depends(authenticate)):
    """Create a Stripe Checkout session for the authenticated org."""
    if body.plan not in ("starter", "professional", "enterprise"):
        raise HTTPException(400, "plan must be starter, professional, or enterprise")
    try:
        url = billing_svc.create_checkout_session(str(ctx.org_id), body.plan, body.success_url, body.cancel_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"checkout_url": url}


from fastapi import Request  # noqa: E402 — already imported via starlette transitively, explicit here


@router.post("/billing/webhook")
async def billing_webhook(request: Request):
    """Stripe webhook endpoint — no auth, verifies Stripe signature."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        result = billing_svc.handle_webhook(payload, sig_header)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


@router.get("/billing/status")
def billing_status(ctx: Ctx = Depends(authenticate)):
    """Return current plan, subscription status, and plan limits."""
    with db(ctx) as conn:
        sub = conn.execute(
            "SELECT plan, status, current_period_end FROM subscriptions WHERE org_id = %s ORDER BY created_at DESC LIMIT 1",
            (ctx.org_id,),
        ).fetchone()
        org = conn.execute("SELECT plan FROM organisations WHERE id = %s", (ctx.org_id,)).fetchone()
        tender_count = conn.execute("SELECT count(*) AS n FROM tenders").fetchone()["n"]
        user_count = conn.execute("SELECT count(*) AS n FROM memberships WHERE org_id = %s", (ctx.org_id,)).fetchone()[
            "n"
        ]
    plan = sub["plan"] if sub else (org["plan"] if org else "starter")
    limits = billing_svc.get_plan_limits(plan)
    return {
        "plan": plan,
        "status": sub["status"] if sub else "none",
        "current_period_end": sub["current_period_end"] if sub else None,
        "limits": limits,
        "usage": {"tenders": tender_count, "users": user_count},
    }


# ---------- admin ----------

admin_router = APIRouter(prefix="/admin")


def require_admin(ctx: Ctx = Depends(authenticate)) -> Ctx:
    ctx.require("admin")
    return ctx


from app.ai_gateway.saas_agent import SaaSAgent  # noqa: E402

_agent = SaaSAgent()


@admin_router.get("/metrics")
def admin_metrics(ctx: Ctx = Depends(require_admin)):
    return _agent.get_platform_metrics()


@admin_router.get("/tenants")
def admin_tenants(ctx: Ctx = Depends(require_admin)):
    import psycopg

    with psycopg.connect(settings.database_url, row_factory=psycopg.rows.dict_row) as conn:
        rows = conn.execute(
            "SELECT o.id, o.name, o.plan, o.stripe_customer_id,"
            " (SELECT count(*) FROM tenders t WHERE t.org_id = o.id) AS tender_count,"
            " (SELECT count(*) FROM memberships m WHERE m.org_id = o.id) AS user_count"
            " FROM organisations o ORDER BY o.created_at DESC"
        ).fetchall()
    return rows


@admin_router.get("/health")
def admin_health(ctx: Ctx = Depends(require_admin)):
    return _agent.check_system_health()


@admin_router.get("/report")
def admin_report(ctx: Ctx = Depends(require_admin)):
    return {"report": _agent.generate_daily_report()}


class PlanChangeIn(BaseModel):
    plan: str


@admin_router.post("/tenant/{org_id}/plan")
def admin_force_plan(org_id: str, body: PlanChangeIn, ctx: Ctx = Depends(require_admin)):
    if body.plan not in ("starter", "professional", "enterprise"):
        raise HTTPException(400, "invalid plan")
    import psycopg

    with psycopg.connect(settings.database_url) as conn:
        conn.execute("UPDATE organisations SET plan = %s WHERE id = %s", (body.plan, uuid.UUID(org_id)))
    return {"org_id": org_id, "plan": body.plan}


# Ordered list matches conftest._delete_org and verify_install.workflow cleanup
_TENANT_DELETE_TABLES = [
    "approvals",
    "draft_claims",
    "revisions",
    "drafts",
    "questions",
    "requirements",
    "doc_blocks",
    "documents",
    "evidence_chunks",
    "evidence_items",
    "export_manifests",
    "audit_events",
    "api_tokens",
    "memberships",
    "tenders",
    "company_profiles",
    "jobs",
    "certificates",
]

_APPEND_ONLY_TRIGGERS = [
    ("revisions", "revisions_append_only"),
    ("audit_events", "audit_append_only"),
]


@admin_router.delete("/tenant/{org_id}", status_code=200)
def admin_delete_tenant(org_id: str, ctx: Ctx = Depends(require_admin)):
    """Tenant roles never grant platform-wide deletion authority."""
    raise HTTPException(403, "tenant deletion requires a separately reviewed platform operation")
