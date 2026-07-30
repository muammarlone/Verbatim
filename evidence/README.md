# Verification Evidence

## Reproducible commands

```powershell
python scripts\validate_architecture.py
python -m pytest
python -m pytest --cov=secure_transcribe --cov-branch --cov-report=term-missing
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
node --check src\secure_transcribe\static\app.js
python -m build --wheel
```

Recorded July 29, 2026; current STS-105/106 results supersede the original architecture/test counts while media/browser recordings remain unchanged:

- Architecture evaluation: `21/21` deterministic gates passed; catalog `1.1.0`, report schema `1.0`
- Tests: `87 passed in 8.46s` in the final full regression
- Python coverage with branch tracking: `84%` (`pytest-cov`)
- Wheel build: pass; console entry point and bundled static UI present
- Ruff: `All checks passed!`
- Compileall: pass
- JavaScript syntax: pass
- Real synthetic API smoke: complete in 16.18 seconds, 9.193-second media, 2 segments, exact 17-word intended fixture, JSON export 200, inline media, no error
- Responsive checks: 1440×1000, 768×900, and 375×812; no console errors, no horizontal overflow, correct completed-state visibility
- Recorded end-to-end demo: 114.52-second narrated H.264/AAC MP4; authorization through deletion; zero browser console errors
- Recording run: real 80.618-second local processing while capture shared the CPU; only the middle of that wait is shown at 12× with an on-screen disclosure
- Demo export: exact 17-word synthetic transcript, `deterministic-extractive-v1` analysis, full model identity, and deletion audit event
- Real batch smoke: 2 MP4s completed in 25.34 seconds; 6 selected outputs plus manifest in QA run; 2 exact synthetic transcript matches
- Batch browser UAT: desktop, tablet, and 375 px mobile; no console errors or horizontal overflow
- Recorded batch demo: 62.2-second narrated H.264/AAC MP4; 2 MP4s × 5 formats; 11 output files; zero managed entries after cleanup

- Manifest preview: strict CSV/XLSX, hostile-feature, secret-reference redaction, request budget, memory expiry/capacity, and reason-code tests passed; near-limit synthetic test call 0.25 seconds.
- Dependency hardening: multipart 0.0.20 produced six direct advisory findings; 0.0.31 isolated overlay passed all 87 tests and the narrowed direct-pin audit returned no known vulnerabilities; full transitive audit remains conditional.

## Architecture evidence

- [Read the architecture index](../ARCHITECTURE.md)
- [Inspect the machine-readable gate catalog](../evals/architecture-evals.json)
- [Inspect the generated 21-gate report](architecture/architecture-eval-report.json)
- [Open the L1-L3 rendered/editable diagram sets](../diagrams)

## Manifest preview evidence

- [Read the STS-105/106 evidence record](manifest-preview/README.md)
- [Inspect machine-readable manifest evidence](manifest-preview/manifest-preview-evidence.json)

## Folder batch demo

- [Watch the batch MP4](batch-demo/verbatim-batch-end-to-end-demo.mp4)
- [Read the batch verification record](batch-demo/README.md)
- [Inspect machine-readable batch evidence](batch-demo/demo-evidence.json)
- [View the batch visual checkpoint sheet](batch-demo/batch-demo-contact-sheet-detailed.png)

## Recorded demo

- [Watch the end-to-end MP4](demo/verbatim-end-to-end-demo.mp4)
- [Read the demo verification record](demo/README.md)
- [Inspect machine-readable demo evidence](demo/demo-evidence.json)
- [View the visual checkpoint sheet](demo/demo-contact-sheet.png)

## Screenshots

- [Desktop overview](screenshots/overview-desktop.png)
- [Desktop review](screenshots/review-desktop.png)
- [Tablet overview](screenshots/overview-tablet.png)
- [Tablet review](screenshots/review-tablet.png)
- [Mobile overview](screenshots/overview-mobile.png)
- [Mobile review](screenshots/review-mobile.png)

These artifacts demonstrate the controlled fixture and UI state only. They do not establish general transcription accuracy, production security, compliance, or user value.
