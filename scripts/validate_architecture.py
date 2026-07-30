from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATOR_VERSION = "1.0"
CHECK_TYPES = {
    "files_exist",
    "forbidden_imports_absent",
    "json_contract",
    "module_dependencies",
    "source_contains",
    "symbols_exist",
    "tests_exist",
}


class CatalogError(ValueError):
    """Raised when the evaluation catalog itself is invalid."""


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    required = {"schema_version", "catalog_version", "system", "evaluations"}
    missing = required - catalog.keys()
    if missing:
        raise CatalogError(f"catalog missing keys: {', '.join(sorted(missing))}")
    if catalog["schema_version"] != "1.0":
        raise CatalogError("unsupported catalog schema_version")
    if not isinstance(catalog["evaluations"], list) or not catalog["evaluations"]:
        raise CatalogError("evaluations must be a non-empty list")
    ids: set[str] = set()
    for evaluation in catalog["evaluations"]:
        gate_required = {
            "id",
            "level",
            "title",
            "critical",
            "check",
            "evidence",
            "failure_action",
        }
        gate_missing = gate_required - evaluation.keys()
        if gate_missing:
            raise CatalogError(
                f"evaluation missing keys: {', '.join(sorted(gate_missing))}"
            )
        if evaluation["id"] in ids:
            raise CatalogError(f"duplicate evaluation id: {evaluation['id']}")
        ids.add(evaluation["id"])
        check_type = evaluation["check"].get("type")
        if check_type not in CHECK_TYPES:
            raise CatalogError(f"unsupported check type for {evaluation['id']}: {check_type}")
    return catalog


def _path(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if candidate != root and not candidate.is_relative_to(root):
        raise CatalogError(f"catalog path leaves repository: {value}")
    return candidate


def _python_tree(root: Path, relative: str) -> ast.Module:
    path = _path(root, relative)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"cannot read Python source {relative}: {exc}") from exc
    try:
        return ast.parse(source, filename=relative)
    except SyntaxError as exc:
        raise CatalogError(f"cannot parse Python source {relative}: {exc}") from exc


def _import_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _top_level_symbols(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _run_check(root: Path, check: dict[str, Any]) -> tuple[bool, list[str]]:
    check_type = check["type"]
    if check_type == "files_exist":
        failures = []
        for relative in check.get("paths", []):
            path = _path(root, relative)
            if not path.is_file() or path.stat().st_size == 0:
                failures.append(f"missing or empty: {relative}")
        return not failures, failures or [f"{len(check.get('paths', []))} files present"]

    if check_type == "symbols_exist":
        failures = []
        count = 0
        for relative, expected in check.get("files", {}).items():
            symbols = _top_level_symbols(_python_tree(root, relative))
            for symbol in expected:
                count += 1
                if symbol not in symbols:
                    failures.append(f"missing symbol {symbol} in {relative}")
        return not failures, failures or [f"{count} required symbols present"]

    if check_type == "source_contains":
        failures = []
        count = 0
        for relative, fragments in check.get("files", {}).items():
            source = _path(root, relative).read_text(encoding="utf-8")
            for fragment in fragments:
                count += 1
                if fragment not in source:
                    failures.append(f"missing required fragment in {relative}: {fragment}")
        return not failures, failures or [f"{count} required source contracts present"]

    if check_type == "forbidden_imports_absent":
        failures = []
        prefixes = tuple(check.get("prefixes", []))
        files = sorted(_path(root, check["root"]).rglob("*.py"))
        for path in files:
            relative = path.relative_to(root).as_posix()
            for name in _import_names(_python_tree(root, relative)):
                if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
                    failures.append(f"forbidden import {name} in {relative}")
        return not failures, failures or [f"{len(files)} production modules inspected"]

    if check_type == "module_dependencies":
        failures = []
        package_root = _path(root, check["root"])
        allowed = {name: set(targets) for name, targets in check.get("allowed", {}).items()}
        modules = set(allowed)
        edge_count = 0
        for path in sorted(package_root.glob("*.py")):
            source_module = path.stem
            if source_module not in allowed:
                failures.append(f"module missing from dependency catalog: {source_module}")
                continue
            relative = path.relative_to(root).as_posix()
            tree = _python_tree(root, relative)
            targets: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.level and node.module:
                        targets.add(node.module.split(".")[0])
                    elif node.module and node.module.startswith(check["package"] + "."):
                        targets.add(node.module.split(".")[1])
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        prefix = check["package"] + "."
                        if alias.name.startswith(prefix):
                            targets.add(alias.name[len(prefix) :].split(".")[0])
            for target in sorted(targets & modules):
                edge_count += 1
                if target not in allowed[source_module]:
                    failures.append(f"undeclared dependency: {source_module} -> {target}")
        return not failures, failures or [f"{edge_count} internal dependency edges allowed"]

    if check_type == "tests_exist":
        failures = []
        count = 0
        for relative, expected in check.get("files", {}).items():
            symbols = _top_level_symbols(_python_tree(root, relative))
            for test_name in expected:
                count += 1
                if test_name not in symbols:
                    failures.append(f"missing regression {test_name} in {relative}")
        return not failures, failures or [f"{count} named regressions traced"]

    if check_type == "json_contract":
        relative = check["path"]
        path = _path(root, relative)
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return False, [f"invalid JSON {relative}: {exc}"]
        failures = []
        for dotted, expected in check.get("equals", {}).items():
            value: Any = payload
            try:
                for part in dotted.split("."):
                    value = value[part]
            except (KeyError, TypeError):
                failures.append(f"missing JSON key {dotted} in {relative}")
                continue
            if value != expected:
                failures.append(f"{relative}:{dotted} expected {expected!r}, found {value!r}")
        return not failures, failures or [f"{len(check.get('equals', {}))} JSON claims matched"]

    raise CatalogError(f"unsupported check type: {check_type}")


def evaluate_catalog(root: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    results = []
    for evaluation in catalog["evaluations"]:
        try:
            passed, details = _run_check(root, evaluation["check"])
        except (CatalogError, OSError, UnicodeError) as exc:
            passed, details = False, [str(exc)]
        results.append(
            {
                "id": evaluation["id"],
                "level": evaluation["level"],
                "title": evaluation["title"],
                "critical": evaluation["critical"],
                "passed": passed,
                "details": details,
                "evidence": evaluation["evidence"],
                "failure_action": evaluation["failure_action"],
            }
        )
    passed_count = sum(item["passed"] for item in results)
    failed = [item["id"] for item in results if not item["passed"]]
    critical_failed = [item["id"] for item in results if item["critical"] and not item["passed"]]
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "failed_ids": failed,
            "critical_failed_ids": critical_failed,
            "validated": not failed and not critical_failed,
        },
    }


def _git_revision(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _catalog_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha256(root: Path) -> str:
    inputs = [
        "ARCHITECTURE.md",
        "README.md",
        "SECURITY.md",
        "architecture",
        "constraints.verified-windows.txt",
        "diagrams",
        "evals",
        "evidence/verification.json",
        "governance",
        "pyproject.toml",
        "requirements.txt",
        "scripts",
        "src",
        "tests",
    ]
    files: list[Path] = []
    for value in inputs:
        path = _path(root, value)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                item
                for item in path.rglob("*")
                if item.is_file()
                and "__pycache__" not in item.parts
                and item.suffix not in {".pyc", ".pyo"}
            )
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_report(root: Path, catalog_path: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    report = evaluate_catalog(root, catalog)
    return {
        "schema_version": "1.0",
        "validator_version": VALIDATOR_VERSION,
        "catalog_version": catalog["catalog_version"],
        "catalog_sha256": _catalog_sha256(catalog_path),
        "system": catalog["system"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_base_revision": _git_revision(root),
        "evaluated_source_sha256": _source_sha256(root),
        **report,
        "claim_boundary": (
            "Architecture structure and traceability for this revision only; not a production, "
            "security, compliance, accessibility, or transcription-accuracy certification."
        ),
    }


def main() -> int:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate the declared L1-L3 architecture.")
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--catalog", type=Path, default=Path("evals/architecture-evals.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/architecture/architecture-eval-report.json"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    catalog_path = args.catalog if args.catalog.is_absolute() else root / args.catalog
    output_path = args.output if args.output.is_absolute() else root / args.output
    try:
        catalog = load_catalog(catalog_path)
        report = build_report(root, catalog_path, catalog)
    except (CatalogError, OSError, json.JSONDecodeError) as exc:
        print(f"ARCHITECTURE EVAL ERROR: {exc}")
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = report["summary"]
    decision = "VALIDATED" if summary["validated"] else "BLOCKED"
    print(
        f"ARCHITECTURE {decision}: {summary['passed']}/{summary['total']} gates passed; "
        f"report={output_path.relative_to(root)}"
    )
    if summary["failed_ids"]:
        print("Failed gates: " + ", ".join(summary["failed_ids"]))
    return 0 if summary["validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
