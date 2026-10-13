"""Compare evals/results/latest.json with evals/thresholds.json. Fails when results are absent or below threshold."""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX_KEYS = {"citations_to_nonexistent_evidence", "analysis_seconds_p90_max"}


def main() -> int:
    thresholds = json.loads((ROOT / "evals" / "thresholds.json").read_text())
    path = ROOT / "evals" / "results" / "latest.json"
    if not path.exists():
        print("FAIL  evals/results/latest.json is missing: run the evaluation suite first")
        return 1
    results = json.loads(path.read_text())
    failed = 0
    for key, limit in thresholds.items():
        if key not in results:
            print(f"FAIL  {key}: no result recorded")
            failed += 1
            continue
        value = results[key]
        ok = value <= limit if key in MAX_KEYS else value >= limit
        print(f"{'PASS' if ok else 'FAIL'}  {key}: {value} (threshold {limit})")
        failed += 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
