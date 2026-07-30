# Cross-Environment Evidence Structure (STS-114)

This directory holds environment-qualified evidence required before any pilot decision.
Each subdirectory corresponds to one execution environment. Evidence slots are **unfilled**
until IT or the domain evaluation lead completes the run on that environment.

## Required environments

| Directory | Environment | Owner | Gate | Status |
|---|---|---|---|---|
| `windows-runner/` | Managed Windows endpoint (production candidate) | IT / security lead | QG-02 | OPEN |
| `docker-qualification/` | Docker qualification image (loopback-only, non-root) | Engineering | QG-02 | OPEN |
| `codespaces/` | GitHub Codespaces synthetic-only env | Engineering | STS-112 | OPEN |
| `offline-regression/` | Air-gapped offline regression run | IT | QG-02 | OPEN |

## Evidence slots per environment

Each environment directory must contain, before pilot:

```
{env}/
  run-metadata.json        # who ran, when, OS/kernel, Python version, image digest
  pytest-results.xml       # JUnit XML from pytest --junitxml
  pytest-coverage.json     # coverage.py JSON report (--cov-report=json)
  negative-controls.json   # results of at least 3 negative-control assertions
  sbom-check.json          # hash-manifest check: FFmpeg + model SHA-256 vs recorded
  claim-boundary.md        # explicit statement of what this environment does NOT prove
```

## Negative controls (all environments)

Each environment run MUST include at least:
1. Confirm `STS_ZOOM_CONNECTOR_ENABLED=false` — verify connector endpoint returns 403.
2. Confirm `STS_MANIFEST_INTAKE_ENABLED=false` — verify manifest route returns 404/403.
3. Confirm upload rejects a file with invalid magic bytes (e.g., renamed `.pdf` as `.mp4`).

## What this structure does NOT prove

- General transcription accuracy on production corporate recordings.
- Regulatory compliance (HIPAA, SOC 2, etc.).
- Performance at enterprise scale.
- Penetration test pass (QG-03 is a separate gate).
- Installer sign/deploy completeness (QG-02 IT action required).

## Claim boundary

ASSUMPTION: None of these environment slots are filled until IT executes on the
managed endpoint and a domain evaluation lead approves the production dataset.
Results from this structure are infrastructure scaffolding only.
