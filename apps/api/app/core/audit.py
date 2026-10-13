"""Append-only audit log with a per-organisation hash chain (blueprint section 18)."""

import hashlib
import json


def _hash(org_id: str, actor_id: str | None, action: str, target: str | None, prev: str | None) -> str:
    payload = json.dumps([org_id, actor_id, action, target, prev or ""], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def record(conn, org_id, actor_id, action: str, target: str | None = None) -> None:
    row = conn.execute("SELECT hash FROM audit_events WHERE org_id = %s ORDER BY id DESC LIMIT 1", (org_id,)).fetchone()
    prev = (row["hash"] if isinstance(row, dict) else row[0]) if row else None
    h = _hash(str(org_id), str(actor_id) if actor_id else None, action, target, prev)
    conn.execute(
        "INSERT INTO audit_events (org_id, actor_id, action, target, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s)",
        (org_id, actor_id, action, target, prev, h),
    )


def verify(conn, org_id) -> tuple[bool, int | None, int]:
    """Return (ok, id of first bad event, number of events)."""
    rows = conn.execute(
        "SELECT id, actor_id, action, target, prev_hash, hash FROM audit_events WHERE org_id = %s ORDER BY id",
        (org_id,),
    ).fetchall()
    prev = None
    for r in rows:
        r = r if isinstance(r, dict) else dict(zip(("id", "actor_id", "action", "target", "prev_hash", "hash"), r))
        expected = _hash(str(org_id), str(r["actor_id"]) if r["actor_id"] else None, r["action"], r["target"], prev)
        if r["prev_hash"] != prev or r["hash"] != expected:
            return False, r["id"], len(rows)
        prev = r["hash"]
    return True, None, len(rows)
