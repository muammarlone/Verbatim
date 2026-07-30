"""Accuracy evaluation harness for STS-104.

IMPORTANT: This harness is infrastructure only. Running it against production
recordings requires the domain evaluation lead to approve:
  - The sealed dataset card (recording provenance, speaker demographics, domain labels)
  - Subgroup thresholds (by language, noise level, speaker count, domain)
  - The consequential-error definition and human review protocol

Until those approvals exist, only synthetic fixtures may be used here.
All results from synthetic fixtures must be labelled as such and may not be
cited as evidence of general accuracy.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .wer import WERResult, evaluate, summary


SYNTHETIC_MARKER = "SYNTHETIC_FIXTURE"


@dataclass
class EvalCase:
    id: str
    reference: str
    hypothesis: str | None = None
    language: str = "en"
    noise_level: str = "clean"
    speaker_count: int = 1
    domain: str = "general"
    source: str = SYNTHETIC_MARKER
    wer_threshold: float = 0.10

    @property
    def is_synthetic(self) -> bool:
        return self.source == SYNTHETIC_MARKER


@dataclass
class EvalRun:
    dataset_id: str
    dataset_source: str
    cases: list[EvalCase]
    results: list[WERResult]
    aggregate: dict

    def to_json(self) -> str:
        return json.dumps(
            {
                "dataset_id": self.dataset_id,
                "dataset_source": self.dataset_source,
                "claim_boundary": (
                    "Synthetic fixtures only; no general accuracy claim is permitted. "
                    "A qualified human reviewer and approved domain dataset are required "
                    "before these results can support a pilot decision."
                )
                if self.dataset_source == SYNTHETIC_MARKER
                else "REQUIRES_DOMAIN_EVAL_LEAD_APPROVAL",
                "aggregate": self.aggregate,
                "cases": [
                    {
                        "id": c.id,
                        "source": c.source,
                        "language": c.language,
                        "noise_level": c.noise_level,
                        "speaker_count": c.speaker_count,
                        "domain": c.domain,
                        "wer": r.wer,
                        "passed": r.wer <= r.threshold,
                    }
                    for c, r in zip(self.cases, self.results)
                ],
            },
            indent=2,
        )


TranscribeFn = Callable[[str, str], str]


def run_eval(
    dataset_id: str,
    cases: list[EvalCase],
    transcribe_fn: TranscribeFn,
    *,
    require_synthetic: bool = True,
) -> EvalRun:
    """Run evaluation for a list of EvalCases using the supplied transcription function.

    Args:
        dataset_id: Unique ID for this evaluation run.
        cases: List of EvalCase objects. Hypothesis may be pre-filled or None (calls transcribe_fn).
        transcribe_fn: Callable(audio_path, language) -> transcript_text.
        require_synthetic: If True, raises if any case is not synthetic (safety guard for CI).
    """
    if require_synthetic:
        non_synthetic = [c for c in cases if not c.is_synthetic]
        if non_synthetic:
            raise ValueError(
                f"Production eval cases require domain evaluation lead approval. "
                f"Non-synthetic cases found: {[c.id for c in non_synthetic]}"
            )

    results: list[WERResult] = []
    for case in cases:
        hyp = case.hypothesis if case.hypothesis is not None else transcribe_fn("", case.language)
        results.append(evaluate(case.reference, hyp, case.wer_threshold))

    dataset_source = (
        SYNTHETIC_MARKER
        if all(c.is_synthetic for c in cases)
        else "MIXED_REQUIRES_APPROVAL"
    )
    return EvalRun(
        dataset_id=dataset_id,
        dataset_source=dataset_source,
        cases=cases,
        results=results,
        aggregate=summary(results),
    )


SYNTHETIC_FIXTURE_CASES = [
    # ── English / general ─────────────────────────────────────────────────────
    EvalCase(
        id="syn-001",
        reference="We will document the local review.",
        hypothesis="We will document the local review.",
        language="en",
        noise_level="clean",
        speaker_count=1,
        domain="general",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-002",
        reference="What should happen next?",
        hypothesis="What should happen next?",
        language="en",
        noise_level="clean",
        speaker_count=1,
        domain="general",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
    # ── English / finance ─────────────────────────────────────────────────────
    EvalCase(
        id="syn-003-imperfect",
        reference="The budget review meeting will proceed as scheduled.",
        hypothesis="The budget review meeting will proceed as scheduled",
        language="en",
        noise_level="clean",
        speaker_count=1,
        domain="finance",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.05,
    ),
    # ── English / medical (domain vocabulary) ─────────────────────────────────
    EvalCase(
        id="syn-004-medical",
        reference="The patient presented with hypertension and tachycardia.",
        hypothesis="The patient presented with hypertension and tachycardia.",
        language="en",
        noise_level="clean",
        speaker_count=1,
        domain="medical",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-005-medical-imperfect",
        reference="Dosage should not exceed two hundred milligrams per day.",
        hypothesis="Dosage should not exceed 200 milligrams per day.",
        language="en",
        noise_level="clean",
        speaker_count=1,
        domain="medical",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.15,
    ),
    # ── English / legal (domain vocabulary) ───────────────────────────────────
    EvalCase(
        id="syn-006-legal",
        reference="The deposition was conducted pursuant to federal rule thirty.",
        hypothesis="The deposition was conducted pursuant to federal rule thirty.",
        language="en",
        noise_level="clean",
        speaker_count=1,
        domain="legal",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
    # ── English / noisy (degraded audio simulation) ───────────────────────────
    EvalCase(
        id="syn-007-noisy",
        reference="Please review the attached documents before the meeting.",
        hypothesis="Please review the attached documents before the meeting",
        language="en",
        noise_level="noisy",
        speaker_count=1,
        domain="general",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-008-noisy-imperfect",
        reference="We need to finalise the contract by end of quarter.",
        hypothesis="We need to finalize the contract by end of quarter.",
        language="en",
        noise_level="noisy",
        speaker_count=1,
        domain="finance",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.10,
    ),
    # ── English / multi-speaker ───────────────────────────────────────────────
    EvalCase(
        id="syn-009-multispeaker",
        reference="Team lead: All systems are go. Engineer: Confirmed, no blockers.",
        hypothesis="Team lead: All systems are go. Engineer: Confirmed, no blockers.",
        language="en",
        noise_level="clean",
        speaker_count=2,
        domain="general",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
    # ── Spanish ───────────────────────────────────────────────────────────────
    EvalCase(
        id="syn-010-es",
        reference="La reunión comenzará a las nueve de la mañana.",
        hypothesis="La reunión comenzará a las nueve de la mañana.",
        language="es",
        noise_level="clean",
        speaker_count=1,
        domain="general",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
    # ── French ────────────────────────────────────────────────────────────────
    EvalCase(
        id="syn-011-fr",
        reference="Le rapport sera prêt avant la fin de la semaine.",
        hypothesis="Le rapport sera prêt avant la fin de la semaine.",
        language="fr",
        noise_level="clean",
        speaker_count=1,
        domain="general",
        source=SYNTHETIC_MARKER,
        wer_threshold=0.0,
    ),
]
