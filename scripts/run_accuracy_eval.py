"""STS-104: CLI runner for synthetic accuracy evaluation harness.

Usage:
    python scripts/run_accuracy_eval.py [--output PATH]

IMPORTANT: This runner is synthetic-only. Production dataset requires
domain evaluation lead approval (dataset card, subgroup thresholds,
human review protocol) before any result can support a pilot decision.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.eval.eval_harness import SYNTHETIC_FIXTURE_CASES, SYNTHETIC_MARKER, run_eval
from tests.eval.wer import summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Verbatim accuracy evaluation (synthetic fixtures)")
    parser.add_argument("--output", default=None, help="Write JSON report to this path")
    args = parser.parse_args()

    print("Verbatim accuracy eval — SYNTHETIC fixtures only")
    print(f"Dataset source : {SYNTHETIC_MARKER}")
    print(f"Cases          : {len(SYNTHETIC_FIXTURE_CASES)}")
    print()

    run = run_eval(
        "synthetic-ci-run",
        SYNTHETIC_FIXTURE_CASES,
        transcribe_fn=lambda audio, lang: "",
        require_synthetic=True,
    )

    agg = run.aggregate
    print(f"Count   : {agg['count']}")
    print(f"Passed  : {agg['passed']}")
    print(f"Failed  : {agg['failed']}")
    if agg["mean_wer"] is not None:
        print(f"Mean WER: {agg['mean_wer']:.4f}")
        print(f"Min WER : {agg['min_wer']:.4f}")
        print(f"Max WER : {agg['max_wer']:.4f}")
    print()

    claim = json.loads(run.to_json()).get("claim_boundary", "")
    print(f"CLAIM BOUNDARY: {claim}")
    print()

    if args.output:
        out = Path(args.output)
        out.write_text(run.to_json(), encoding="utf-8")
        print(f"Report written: {out}")

    return 0 if agg["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
