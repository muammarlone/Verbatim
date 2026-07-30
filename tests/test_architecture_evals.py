from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_architecture import evaluate_catalog, load_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _catalog(evaluation: dict) -> dict:
    return {
        "schema_version": "1.0",
        "catalog_version": "test",
        "system": "fixture",
        "evaluations": [evaluation],
    }


def _gate(check: dict) -> dict:
    return {
        "id": "TEST-01",
        "level": "L2",
        "title": "fixture",
        "critical": True,
        "check": check,
        "evidence": [],
        "failure_action": "stop",
    }


def test_repository_l1_l3_architecture_catalog_passes() -> None:
    catalog = load_catalog(PROJECT_ROOT / "evals" / "architecture-evals.json")

    report = evaluate_catalog(PROJECT_ROOT, catalog)

    assert report["summary"]["validated"] is True
    assert report["summary"]["failed_ids"] == []


def test_forbidden_import_eval_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "src" / "example"
    source.mkdir(parents=True)
    (source / "unsafe.py").write_text("import requests\n", encoding="utf-8")
    catalog = _catalog(
        _gate(
            {
                "type": "forbidden_imports_absent",
                "root": "src/example",
                "prefixes": ["requests"],
            }
        )
    )

    report = evaluate_catalog(tmp_path, catalog)

    assert report["summary"]["validated"] is False
    assert report["summary"]["critical_failed_ids"] == ["TEST-01"]
    assert "forbidden import requests" in report["results"][0]["details"][0]


def test_module_dependency_eval_rejects_unapproved_edge(tmp_path: Path) -> None:
    source = tmp_path / "src" / "example"
    source.mkdir(parents=True)
    (source / "api.py").write_text("from .domain import run\n", encoding="utf-8")
    (source / "domain.py").write_text("def run():\n    return None\n", encoding="utf-8")
    catalog = _catalog(
        _gate(
            {
                "type": "module_dependencies",
                "root": "src/example",
                "package": "example",
                "allowed": {"api": [], "domain": []},
            }
        )
    )

    report = evaluate_catalog(tmp_path, catalog)

    assert report["summary"]["validated"] is False
    assert report["results"][0]["details"] == ["undeclared dependency: api -> domain"]


def test_catalog_rejects_duplicate_eval_ids(tmp_path: Path) -> None:
    evaluation = _gate({"type": "files_exist", "paths": []})
    payload = _catalog(evaluation)
    payload["evaluations"].append(evaluation)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    try:
        load_catalog(path)
    except ValueError as exc:
        assert "duplicate evaluation id" in str(exc)
    else:
        raise AssertionError("duplicate architecture evaluation IDs must be rejected")
