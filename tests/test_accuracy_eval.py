"""STS-104: Accuracy evaluation harness tests.

All cases here use SYNTHETIC_MARKER fixtures only. A sealed production
dataset requires domain evaluation lead approval before QG-01 can pass.
"""
from __future__ import annotations

import pytest

from tests.eval.wer import WERResult, batch_wer, evaluate, summary, word_error_rate
from tests.eval.eval_harness import (
    SYNTHETIC_FIXTURE_CASES,
    SYNTHETIC_MARKER,
    EvalCase,
    run_eval,
)


# ── WER utility ──────────────────────────────────────────────────────────────

def test_wer_exact_match():
    assert word_error_rate("hello world", "hello world") == 0.0


def test_wer_single_substitution():
    wer = word_error_rate("hello world", "hello there")
    assert abs(wer - 0.5) < 1e-9  # 1 sub / 2 ref words


def test_wer_one_deletion():
    wer = word_error_rate("the quick brown fox", "the quick fox")
    assert abs(wer - 0.25) < 1e-9  # 1 del / 4 ref words


def test_wer_one_insertion():
    wer = word_error_rate("hello world", "hello big world")
    assert abs(wer - 0.5) < 1e-9  # 1 ins / 2 ref words


def test_wer_empty_reference_empty_hypothesis():
    assert word_error_rate("", "") == 0.0


def test_wer_empty_reference_nonempty_hypothesis():
    result = word_error_rate("", "extra words")
    assert result == float("inf")


def test_wer_normalized_case_and_punctuation():
    wer = word_error_rate("Hello, World!", "hello world")
    assert wer == 0.0


def test_wer_above_one_possible():
    # 3 insertions on 1-word reference
    wer = word_error_rate("cat", "the big black cat")
    assert wer > 1.0


def test_evaluate_returns_wer_result():
    result = evaluate("meeting notes are ready", "meeting notes are ready")
    assert isinstance(result, WERResult)
    assert result.wer == 0.0
    assert result.ref_words == 4


def test_evaluate_threshold_pass():
    result = evaluate("four word sentence here", "four word sentence here", threshold=0.10)
    assert result.wer <= result.threshold


def test_evaluate_threshold_fail():
    result = evaluate("one two three four five", "one two three", threshold=0.10)
    assert result.wer > result.threshold


def test_batch_wer_multiple_pairs():
    pairs = [
        ("hello world", "hello world"),
        ("the quick fox", "the quick brown fox"),
    ]
    results = batch_wer(pairs, threshold=0.10)
    assert len(results) == 2
    assert results[0].wer == 0.0
    assert results[1].wer > 0.0


def test_summary_all_pass():
    results = batch_wer([("hello world", "hello world")] * 5, threshold=0.10)
    s = summary(results)
    assert s["count"] == 5
    assert s["passed"] == 5
    assert s["failed"] == 0
    assert s["mean_wer"] == 0.0


def test_summary_empty():
    s = summary([])
    assert s["count"] == 0
    assert s["mean_wer"] is None


# ── Eval harness ─────────────────────────────────────────────────────────────

def test_synthetic_fixture_cases_are_marked():
    for case in SYNTHETIC_FIXTURE_CASES:
        assert case.is_synthetic
        assert case.source == SYNTHETIC_MARKER


def test_run_eval_synthetic_exact_match():
    run = run_eval(
        "test-exact-match",
        [SYNTHETIC_FIXTURE_CASES[0]],
        transcribe_fn=lambda audio, lang: "",  # not called; hypothesis pre-filled
        require_synthetic=True,
    )
    assert run.aggregate["count"] == 1
    assert run.aggregate["passed"] == 1
    assert run.dataset_source == SYNTHETIC_MARKER


def test_run_eval_blocks_production_cases():
    production_case = EvalCase(
        id="prod-001",
        reference="real recording text",
        source="s3://corporate-bucket/recordings/2026-07.mp4",
        wer_threshold=0.10,
    )
    with pytest.raises(ValueError, match="Production eval cases require"):
        run_eval(
            "blocked-run",
            [production_case],
            transcribe_fn=lambda audio, lang: "",
            require_synthetic=True,
        )


def test_run_eval_all_synthetic_fixtures():
    run = run_eval(
        "synthetic-full-suite",
        SYNTHETIC_FIXTURE_CASES,
        transcribe_fn=lambda audio, lang: "",
        require_synthetic=True,
    )
    assert run.aggregate["count"] == len(SYNTHETIC_FIXTURE_CASES)
    assert run.dataset_source == SYNTHETIC_MARKER


def test_run_eval_json_output_has_claim_boundary():
    run = run_eval(
        "boundary-check",
        [SYNTHETIC_FIXTURE_CASES[0]],
        transcribe_fn=lambda audio, lang: "",
        require_synthetic=True,
    )
    data = run.to_json()
    assert "claim_boundary" in data
    assert "general accuracy" in data.lower() or "synthetic" in data.lower()


def test_run_eval_json_output_has_case_results():
    import json
    run = run_eval(
        "json-check",
        SYNTHETIC_FIXTURE_CASES,
        transcribe_fn=lambda audio, lang: "",
        require_synthetic=True,
    )
    parsed = json.loads(run.to_json())
    assert len(parsed["cases"]) == len(SYNTHETIC_FIXTURE_CASES)
    for case_result in parsed["cases"]:
        assert "wer" in case_result
        assert "passed" in case_result
        assert case_result["source"] == SYNTHETIC_MARKER


def test_eval_case_imperfect_fixture_within_threshold():
    syn003 = SYNTHETIC_FIXTURE_CASES[2]
    result = evaluate(syn003.reference, syn003.hypothesis, syn003.wer_threshold)
    assert result.wer <= result.threshold
