from copy import deepcopy
from pathlib import Path

from scripts.validate_quality_gates import evaluate_quality_roadmap, load_roadmap


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_quality_roadmap_is_traceable_and_blocks_premature_promotion() -> None:
    report = evaluate_quality_roadmap(
        PROJECT_ROOT,
        load_roadmap(PROJECT_ROOT / "evals" / "quality-roadmap.json"),
    )

    assert report["summary"]["validated"] is True
    assert report["promotion_ready"] is False
    assert report["promotion_blockers"] == [
        "QG-01",
        "QG-02",
        "QG-03",
        "QG-04",
        "QG-05",
        "QG-06",
    ]


def test_quality_roadmap_rejects_a_production_claim_with_open_gates() -> None:
    roadmap = deepcopy(load_roadmap(PROJECT_ROOT / "evals" / "quality-roadmap.json"))
    roadmap["production_claim_allowed"] = True

    report = evaluate_quality_roadmap(PROJECT_ROOT, roadmap)

    assert report["summary"]["validated"] is False
    assert "production claim must remain disabled" in " ".join(report["summary"]["errors"])
