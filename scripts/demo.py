"""Run the sample tender through a running server (http://localhost:8000) and save the Word export.

python scripts/demo.py            # then open the saved file
"""

import json
import pathlib
import sys
import uuid

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def main() -> None:
    c = httpx.Client(base_url=BASE + "/v1", timeout=60)
    acct = c.post(
        "/signup", json={"org_name": "Demo Bids Ltd", "email": f"demo-{uuid.uuid4().hex[:6]}@example.test"}
    ).json()
    h = {"Authorization": f"Bearer {acct['token']}"}
    tender = c.post("/tenders", json={"title": "Riverside Council: Digital Services"}, headers=h).json()
    up = c.post(
        f"/tenders/{tender['id']}/documents",
        headers=h,
        files={"file": ("tender.txt", (ROOT / "samples" / "sample_tender.txt").read_bytes())},
    ).json()
    print(f"read {up['blocks']} blocks, found {up['requirements']} requirements and {up['questions']} questions")
    for e in json.loads((ROOT / "samples" / "sample_evidence.json").read_text()):
        c.post("/evidence", headers=h, json={**e, "approved": True})
    for q in c.get(f"/tenders/{tender['id']}/questions", headers=h).json():
        d = c.post(f"/questions/{q['id']}/drafts", headers=h).json()
        print(
            f"draft v{d['version']}: {d['word_count']} words, claims "
            f"{[x['status'] for x in d['claims']]}, AI text kept {d['ai_retained_ratio']:.0%}"
        )
        c.post(f"/drafts/{d['id']}/approve", headers=h)
    r = c.get(f"/tenders/{tender['id']}/export", headers=h)
    out = ROOT / "data" / "demo_submission.docx"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    print(f"export {r.status_code}, saved to {out} (sha256 {r.headers['x-export-sha256'][:16]}...)")


if __name__ == "__main__":
    main()
