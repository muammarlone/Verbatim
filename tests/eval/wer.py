"""Word-error rate and meaning-impact measurement utilities for STS-104.

WER = (Substitutions + Deletions + Insertions) / Reference word count.
This implementation uses dynamic programming (Wagner-Fischer algorithm).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence


def _normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return text.split()


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Return WER in [0.0, ∞). Values >1.0 indicate more errors than reference words."""
    ref = _normalize(reference)
    hyp = _normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else float("inf")
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[m] / n


@dataclass(frozen=True)
class WERResult:
    reference: str
    hypothesis: str
    wer: float
    ref_words: int
    edit_distance: int

    @property
    def passed(self) -> bool:
        return self.wer <= self.threshold

    threshold: float = 0.10  # default 10% WER ceiling


def evaluate(reference: str, hypothesis: str, threshold: float = 0.10) -> WERResult:
    ref_words = _normalize(reference)
    hyp_words = _normalize(hypothesis)
    wer = word_error_rate(reference, hypothesis)
    n, m = len(ref_words), len(hyp_words)
    edit_dist = round(wer * n) if n > 0 else 0
    return WERResult(
        reference=reference,
        hypothesis=hypothesis,
        wer=wer,
        ref_words=n,
        edit_distance=edit_dist,
        threshold=threshold,
    )


def batch_wer(pairs: Sequence[tuple[str, str]], threshold: float = 0.10) -> list[WERResult]:
    """Evaluate WER for a list of (reference, hypothesis) pairs."""
    return [evaluate(ref, hyp, threshold) for ref, hyp in pairs]


def summary(results: list[WERResult]) -> dict:
    """Aggregate WER summary with pass/fail breakdown."""
    if not results:
        return {"count": 0, "mean_wer": None, "passed": 0, "failed": 0}
    total_wer = sum(r.wer for r in results)
    return {
        "count": len(results),
        "mean_wer": total_wer / len(results),
        "passed": sum(1 for r in results if r.wer <= r.threshold),
        "failed": sum(1 for r in results if r.wer > r.threshold),
        "max_wer": max(r.wer for r in results),
        "min_wer": min(r.wer for r in results),
    }
