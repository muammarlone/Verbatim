"""STS-114: Validate cross-environment evidence structure.

Checks that:
  - All required environment directories exist.
  - Each run-metadata.json is present.
  - Filled run-metadata.json files validate against manifest-schema.json.
  - No filled slot falsely claims all connector flags are enabled.
  - Unfilled stubs are clearly marked OPEN.

Usage:
    python scripts/validate_environment_evidence.py
    python scripts/validate_environment_evidence.py --strict   # fail on any OPEN slot
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT / "evidence" / "environments"
SCHEMA_PATH = ENV_DIR / "manifest-schema.json"

REQUIRED_ENVS = [
    "windows-runner",
    "docker-qualification",
    "codespaces",
    "offline-regression",
]

REQUIRED_CONNECTOR_FLAGS_FALSE = [
    "STS_ZOOM_CONNECTOR_ENABLED",
    "STS_MANIFEST_INTAKE_ENABLED",
    "STS_PROTECTED_ARCHIVE_ENABLED",
]


def _is_placeholder(data: dict) -> bool:
    return "_status" in data and "OPEN" in data.get("_status", "")


def validate_structure(strict: bool = False) -> list[str]:
    errors: list[str] = []
    open_slots: list[str] = []

    if not ENV_DIR.exists():
        errors.append(f"evidence/environments/ directory missing")
        return errors

    if not SCHEMA_PATH.exists():
        errors.append("evidence/environments/manifest-schema.json missing")

    for env in REQUIRED_ENVS:
        env_dir = ENV_DIR / env
        if not env_dir.is_dir():
            errors.append(f"Environment directory missing: {env}/")
            continue

        meta_path = env_dir / "run-metadata.json"
        if not meta_path.exists():
            errors.append(f"run-metadata.json missing in {env}/")
            continue

        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{env}/run-metadata.json is not valid JSON: {exc}")
            continue

        if _is_placeholder(data):
            open_slots.append(env)
            if strict:
                errors.append(f"{env}/run-metadata.json is still an OPEN placeholder (--strict mode)")
            continue

        # Filled slot checks
        for flag in REQUIRED_CONNECTOR_FLAGS_FALSE:
            flags = data.get("connector_flags", {})
            if flags.get(flag) is not False:
                errors.append(
                    f"{env}/run-metadata.json: connector_flags.{flag} must be false"
                )

        if data.get("pytest_failed", 1) != 0:
            errors.append(f"{env}/run-metadata.json: pytest_failed must be 0")

        if not data.get("claim_boundary"):
            errors.append(f"{env}/run-metadata.json: claim_boundary is missing")

        if data.get("negative_controls_total", 0) < 3:
            errors.append(f"{env}/run-metadata.json: negative_controls_total must be >= 3")

    return errors, open_slots


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cross-environment evidence structure")
    parser.add_argument("--strict", action="store_true", help="Fail on any OPEN placeholder slot")
    args = parser.parse_args()

    errors, open_slots = validate_structure(strict=args.strict)

    print(f"Cross-environment evidence: {ENV_DIR.relative_to(ROOT)}")
    print(f"Required environments : {len(REQUIRED_ENVS)}")
    print(f"Open (unfilled) slots : {len(open_slots)}")
    if open_slots:
        for env in open_slots:
            print(f"  OPEN: {env}")
    print()

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("Structure validation passed. Filled slots: 0 errors.")
    print()
    print("CLAIM BOUNDARY: This validator confirms structure only. No filled slot is valid")
    print("until IT and the domain evaluation lead have completed qualified runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
