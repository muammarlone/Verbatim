# Quality Hardening Evidence

This packet supports STS-116 and the
[principal-architect roadmap](../../governance/QUALITY_ROADMAP.md). It improves measurable
quality without claiming corporate-pilot or production readiness.

## Reproduce

```powershell
python scripts\run_browser_quality_uat.py
python scripts\validate_quality_gates.py --write-report
python scripts\validate_architecture.py
python -m pytest --cov=secure_transcribe --cov-branch
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
node --check src\secure_transcribe\static\app.js
python -m build --wheel
python -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off
```

Regenerate the direct-pin evidence with:

```powershell
python -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off --format json --output evidence\quality\direct-dependency-audit.json
python -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off --format cyclonedx-json --output evidence\quality\direct-dependency-sbom.cdx.json
```

## Evidence

- `browser-uat.json`: four Chromium cases and deterministic pass/fail checks.
- `mobile-light.png` and `desktop-dark.png`: visual checkpoints inspected after the run.
- `direct-dependency-audit.json`: direct pinned dependencies with advisory results.
- `direct-dependency-sbom.cdx.json`: CycloneDX 1.4 direct-pin inventory.
- `quality-gate-report.json`: current gate validation, promotion blockers, and evidence hashes.

## Claim boundary

The direct audit uses `--no-deps`; it is not a full transitive audit. Browser automation is not
a supported-screen-reader test or an independent penetration test. The gate report must remain
`promotion_ready: false` until all six promotion-blocking owner domains provide passing evidence.
