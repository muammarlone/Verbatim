from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "evals" / "quality-roadmap.json"
REPORT = ROOT / "evidence" / "quality" / "quality-gate-report.json"
ALLOWED_STATUSES = {"passed", "partial", "blocked", "not_started"}
REQUIRED_GATES = {f"QG-{number:02d}" for number in range(1, 9)}
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def local_link_errors(path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        clean = unquote(target.split("#", 1)[0].strip())
        if not clean or clean.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (path.parent / clean).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.exists():
            errors.append(f"{path.relative_to(root)}: broken local link {target}")
    return errors


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_roadmap(path: Path = ROADMAP) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def direct_requirements(root: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw_line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("==") != 1:
            raise ValueError(f"runtime requirement must use one exact pin: {line}")
        name, version = line.split("==")
        pins[name.lower()] = version
    return pins


def evaluate_quality_roadmap(root: Path, roadmap: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for document in (
        root / "governance" / "QUALITY_ROADMAP.md",
        root / "governance" / "QUALITY_HARDENING_ASSESSMENT.md",
        root / "evidence" / "quality" / "README.md",
    ):
        if not document.is_file():
            errors.append(f"missing quality document: {document.relative_to(root)}")
        else:
            errors.extend(local_link_errors(document, root))
    gates = roadmap.get("gates", [])
    gate_ids = [gate.get("id") for gate in gates]
    duplicate_ids = sorted(gate_id for gate_id, count in Counter(gate_ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate quality gate IDs: {', '.join(duplicate_ids)}")
    missing_gates = sorted(REQUIRED_GATES - set(gate_ids))
    if missing_gates:
        errors.append(f"missing required quality gates: {', '.join(missing_gates)}")

    backlog = (root / "governance" / "BACKLOG.md").read_text(encoding="utf-8")
    risks = (root / "governance" / "RISK_REGISTER.md").read_text(encoding="utf-8")
    results: list[dict[str, Any]] = []
    for gate in gates:
        gate_id = str(gate.get("id", "<missing>"))
        gate_errors: list[str] = []
        status = gate.get("status")
        if status not in ALLOWED_STATUSES:
            gate_errors.append(f"unsupported status: {status}")
        for field in ("title", "owner_role", "next_action"):
            if not str(gate.get(field, "")).strip():
                gate_errors.append(f"missing {field}")
        if len(gate.get("exit_criteria", [])) < 2:
            gate_errors.append("at least two exit criteria are required")
        blockers = gate.get("blockers", [])
        if status == "passed" and blockers:
            gate_errors.append("passed gate cannot retain blockers")
        if status != "passed" and not blockers:
            gate_errors.append("open gate must state at least one blocker")
        for story in gate.get("linked_stories", []):
            if story not in backlog:
                gate_errors.append(f"unknown linked story: {story}")
        for risk in gate.get("linked_risks", []):
            if risk not in risks:
                gate_errors.append(f"unknown linked risk: {risk}")
        evidence_hashes: dict[str, str] = {}
        for relative in gate.get("evidence", []):
            evidence_path = root / relative
            if not evidence_path.is_file():
                gate_errors.append(f"missing evidence: {relative}")
            else:
                evidence_hashes[relative] = sha256(evidence_path)
        errors.extend(f"{gate_id}: {error}" for error in gate_errors)
        results.append(
            {
                "id": gate_id,
                "status": status,
                "promotion_blocking": bool(gate.get("promotion_blocking")),
                "validated": not gate_errors,
                "errors": gate_errors,
                "evidence_sha256": evidence_hashes,
            }
        )

    promotion_blockers = sorted(
        result["id"]
        for result in results
        if result["promotion_blocking"] and result["status"] != "passed"
    )
    promotion_ready = not promotion_blockers and not errors
    if promotion_blockers and roadmap.get("production_claim_allowed") is not False:
        errors.append("production claim must remain disabled while promotion blockers are open")
    if promotion_blockers and roadmap.get("decision") != "proceed_with_conditions":
        errors.append("open promotion blockers require a proceed_with_conditions decision")

    audit_path = root / "evidence" / "quality" / "direct-dependency-audit.json"
    sbom_path = root / "evidence" / "quality" / "direct-dependency-sbom.cdx.json"
    if audit_path.is_file() and sbom_path.is_file():
        pins = direct_requirements(root)
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audited = {
            item["name"].lower(): item["version"] for item in audit.get("dependencies", [])
        }
        if audited != pins:
            errors.append("direct dependency audit does not match requirements.txt")
        vulnerable = [
            item["name"] for item in audit.get("dependencies", []) if item.get("vulns")
        ]
        if vulnerable:
            errors.append(f"direct dependency advisories remain: {', '.join(vulnerable)}")
        sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
        components = {
            item["name"].lower(): item["version"] for item in sbom.get("components", [])
        }
        if components != pins:
            errors.append("direct dependency SBOM does not match requirements.txt")

    status_counts = Counter(result["status"] for result in results)
    return {
        "schema_version": "1.0",
        "roadmap_version": roadmap.get("roadmap_version"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": roadmap.get("decision"),
        "promotion_target": roadmap.get("promotion_target"),
        "promotion_ready": promotion_ready,
        "promotion_blockers": promotion_blockers,
        "summary": {
            "total": len(results),
            "passed": status_counts["passed"],
            "partial": status_counts["partial"],
            "blocked": status_counts["blocked"],
            "not_started": status_counts["not_started"],
            "validated": not errors,
            "errors": errors,
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the principal-architect quality roadmap.")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    report = evaluate_quality_roadmap(ROOT, load_roadmap())
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["summary"]["validated"]:
        for error in report["summary"]["errors"]:
            print(f"FAIL: {error}")
        raise SystemExit(1)
    print(
        "QUALITY ROADMAP VALIDATED: "
        f"{report['summary']['total']} gates traced; "
        f"promotion_ready={str(report['promotion_ready']).lower()}; "
        f"blockers={','.join(report['promotion_blockers'])}"
    )


if __name__ == "__main__":
    main()
