# Codespaces / Devcontainer Stop Gate

**Read before running Verbatim in this environment.**

## What this environment is for

Synthetic and mock testing only. Contributors can run the full test suite, develop against fake
fixtures, and verify the application's API contract without touching production data or credentials.

## Hard limits — these are not configuration options

| Prohibited | Why |
|---|---|
| Corporate recordings (MP4, M4A, MP3, WAV, etc.) | Audio may contain PHI/PII/BHI/BII; Codespaces may sync to cloud |
| Production Whisper model artifact | Model may have proprietary training data lineage |
| Real Zoom application credentials | Codespaces is an external SaaS boundary |
| Production Windows Credential Locker entries | Credentials must stay on the managed endpoint |
| `STS_MANIFEST_INTAKE_ENABLED=true` in Codespaces | Activates credential-adjacent code before threat model is complete |
| `STS_PROTECTED_ARCHIVE_ENABLED=true` | Not implemented; flag reserved for post-gate work |
| `STS_ZOOM_CONNECTOR_ENABLED=true` | Not implemented; requires Zoom Marketplace approval |

## What you can do

- Run `python -m pytest` — all 334 tests pass (16 skip on unfilled env placeholders)
- Use `STS_DATA_DIR` pointing to `data/codespaces-dev/` (set by devcontainer.json)
- Upload synthetic test recordings (the `tests/fixtures/` MP4 is safe)
- Test the manifest preview with synthetic CSV fixtures

## If you are asked to use production data in Codespaces

Stop. Consult the endpoint security and privacy leads. The correct environment for production
recordings is the qualified managed Windows endpoint defined in QG-03 and QG-06.

## Linked gates

- QG-02: Supply chain (signed deployment not available in Codespaces)
- QG-03: Identity and storage isolation (Codespaces uses GitHub identity, not corporate)
- STS-112: This devcontainer is the acceptance deliverable for STS-112
