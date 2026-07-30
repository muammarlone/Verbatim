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
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.eval.eval_harness import SYNTHETIC_FIXTURE_CASES, SYNTHETIC_MARKER, run_eval
from tests.eval.wer import WERResult, summary


def _subgroup_summary(cases, results, key: str) -> dict:
    """Return per-value summary dict for a case attribute (language/noise_level/domain)."""
    groups: dict[str, list[WERResult]] = defaultdict(list)
    for case, result in zip(cases, results):
        groups[getattr(case, key)].append(result)
    return {
        value: summary(group_results)
        for value, group_results in sorted(groups.items())
    }


def _print_subgroup(label: str, breakdown: dict) -> None:
    print(f"  {label}:")
    for value, stats in breakdown.items():
        passed = stats["passed"]
        total = stats["count"]
        mean = f"{stats['mean_wer']:.4f}" if stats["mean_wer"] is not None else "n/a"
        print(f"    {value:<18} {passed}/{total} passed  mean WER {mean}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verbatim accuracy evaluation (synthetic fixtures)")
    parser.add_argument("--output", default=None, help="Write JSON report to this path")
    parser.add_argument("--subgroups", action="store_true", help="Print subgroup breakdown")
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

    if args.subgroups or True:  # always print subgroups for eval-lead review
        print("Subgroup breakdown (synthetic only — domain eval lead must seal production set):")
        _print_subgroup("By language", _subgroup_summary(run.cases, run.results, "language"))
        _print_subgroup("By noise", _subgroup_summary(run.cases, run.results, "noise_level"))
        _print_subgroup("By domain", _subgroup_summary(run.cases, run.results, "domain"))
        print()

    claim = json.loads(run.to_json()).get("claim_boundary", "")
    print(f"CLAIM BOUNDARY: {claim}")
    print()

    if args.output:
        out = Path(args.output)
        report = json.loads(run.to_json())
        report["subgroups"] = {
            "language": _subgroup_summary(run.cases, run.results, "language"),
            "noise_level": _subgroup_summary(run.cases, run.results, "noise_level"),
            "domain": _subgroup_summary(run.cases, run.results, "domain"),
        }
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written: {out}")

    return 0 if agg["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
