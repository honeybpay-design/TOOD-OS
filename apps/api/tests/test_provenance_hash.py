from app.provenance.hashchain import Revision, ai_retained_ratio, compute_hash, verify_chain


def _chain(n=3):
    revs, prev = [], None
    for i in range(n):
        content, meta = {"text": f"v{i}"}, {"actor": "u1"}
        h = compute_hash(content, meta, prev)
        revs.append(Revision(content, meta, prev, h))
        prev = h
    return revs


def test_valid_chain_verifies():
    assert verify_chain(_chain()) == (True, None)


def test_tampering_is_detected_at_the_right_revision():
    revs = _chain()
    revs[1].content["text"] = "edited later"
    assert verify_chain(revs) == (False, 1)


def test_removed_revision_is_detected():
    revs = _chain()
    del revs[1]
    assert verify_chain(revs)[0] is False


def test_ai_retained_ratio():
    spans = [{"origin": "ai", "length": 30}, {"origin": "human", "length": 70}]
    assert ai_retained_ratio(spans) == 0.3
    assert ai_retained_ratio([]) == 0.0
