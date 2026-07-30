from pathlib import Path

from scripts.validate_product_evidence import validate_product_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_product_documentation_and_explainer_are_grounded() -> None:
    assert validate_product_evidence(PROJECT_ROOT, verify_streams=False) == []
