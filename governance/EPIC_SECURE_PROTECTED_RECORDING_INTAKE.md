# Epic: Secure Manifest-Driven Zoom and Protected-Recording Bulk Intake

Status: approved backlog specification; implementation is feature-flagged off until its child gates pass.

Tracking issue: [GitHub issue #1](https://github.com/muammarlone/Verbatim/issues/1)

## Context

Authorized reviewers need to process up to 25 protected recordings without manually downloading, unlocking, and importing every MP4. Verbatim currently accepts direct local MP4 files only, keeps networking disabled, and applies one language/output configuration to the entire batch.

This epic introduces bounded CSV/XLSX intake, protected-archive extraction, optional Zoom retrieval, corporate installation, reproducible container testing, and a UI/UX fast follow. Passwords, OAuth credentials, and corporate recordings must never enter source control, spreadsheets, logs, Codespaces, or test evidence.

## Verified current state

Verified July 29, 2026.

| Capability | Current behavior | Gap |
|---|---|---|
| Folder batch | Scans direct, nonrecursive MP4 files under `STS_BATCH_ROOT` | No manifest or protected container |
| Batch limit | Maximum 25 files and 10 GiB | Preserve for first release |
| Networking | `/api/session` reports `network_required: false` | Zoom requires an optional outbound connector |
| Credentials | In-memory mutation token only | No credential-provider abstraction |
| Installation | PowerShell launcher and wheelhouse instructions | No signed enterprise installer |
| Containers/Codespaces | No Dockerfile or devcontainer | No reproducible synthetic qualification environment |
| UI | Folder and upload workflows | No manifest preview, authentication, or per-source recovery UX |

Implementation evidence: `src/secure_transcribe/models.py:64-102`, `src/secure_transcribe/batch.py:189-330`, `src/secure_transcribe/app.py:200-283`, `Start-Verbatim.ps1`, and `SECURITY.md`.

## Proposed architecture

```text
CSV/XLSX
   |
   v
Strict manifest parser -> sanitized preview -> consent gate
                                                |
                    +---------------------------+--------------------------+
                    |                                                      |
         Protected archive adapter                              Zoom OAuth connector
                    |                                                      |
       prompt/wincred secret provider                       user OAuth + PKCE token
                    +---------------------------+--------------------------+
                                                |
                                                v
                              Existing managed MP4 batch pipeline
                                                |
                                                v
                           TXT/SRT/VTT/MD/JSON + manifest + audit
```

The existing `JobProcessor`, transcription engine, deterministic analysis, export, deletion, and retention contracts remain unchanged. Manifest, archive, and Zoom paths ship behind separate disabled-by-default feature flags.

### Manifest contract

Accepted formats and budgets:

- UTF-8 CSV or `.xlsx` with exactly one visible worksheet named `recordings`.
- Maximum workbook size: 5 MiB; maximum data rows: 25; exactly seven columns.
- Reject `.xls`, `.xlsm`, formulas, macros, external links, merged cells, hidden rows/columns, duplicate row IDs, unknown columns, and extra worksheets.

| Column | Rule |
|---|---|
| `schema_version` | Required; exactly `1.0` |
| `row_id` | Required unique ASCII identifier, 1-64 characters |
| `source_type` | `local_archive` or `zoom_recording` |
| `source_locator` | Relative archive path or validated Zoom recording/file identifier; never an arbitrary URL |
| `secret_ref` | `prompt://label`, `wincred://target`, or blank for Zoom OAuth |
| `display_name` | Required display metadata; never a filesystem path |
| `expected_sha256` | Optional lowercase SHA-256 digest |

Output folder, export formats, language, authorization confirmation, and budgets remain explicit global UI controls. Workbook content cannot enable connectors, change retention, select arbitrary hosts, overwrite outputs, or weaken limits.

### API contracts

- `POST /api/import-plans/preview`: mutation token plus multipart CSV/XLSX; returns sanitized rows, deterministic errors, manifest SHA-256, and a 30-minute plan ID; resolves no secret and downloads no media.
- `POST /api/import-plans/{plan_id}/execute`: requires consent, output folder, formats, language, and optional prompt-secret values; prompt values remain memory-only; creates one managed batch with immutable manifest provenance.
- `GET /api/connectors/zoom/status`: returns `disabled`, `authorization_required`, `ready`, or `attention`; never exposes account or credential data.
- `POST /api/connectors/zoom/authorize`: starts user-managed OAuth with PKCE and state verification.
- `DELETE /api/connectors/zoom/authorization`: revokes/removes the refresh credential and disables retrieval.

### Secret contract

- Zoom uses user-authorized OAuth with PKCE. Account-wide server-to-server access is out of scope.
- Only the Zoom refresh credential is stored in Windows Credential Locker.
- Archive passwords use `prompt://` or `wincred://`; the manifest may reference at most 20 distinct `wincred://` targets.
- Secrets cannot appear in persisted plans/manifests, batch records, audit, URLs, subprocess arguments, environment variables, error messages, screenshots, or evidence.
- Password attempts are limited to three per source. Secret references are released immediately after acquisition/extraction.

### Protected archive contract

- Initial formats: encrypted ZIP and 7z containing direct MP4 entries.
- Reject nested archives, non-MP4 entries, symlinks/junctions, absolute paths, traversal, duplicate normalized names, and recursive directories.
- A security spike selects an extraction implementation only after proving secret-safe invocation, AES support, timeout/cancellation, provenance, and cleanup. Candidates exposing passwords through process arguments or environment variables are rejected.
- Enforce expanded entry count, per-file bytes, aggregate bytes, compression-ratio, and elapsed-time limits.
- Extract into a UUID-managed temporary directory removed after success, failure, cancellation, timeout, or restart recovery.

### Zoom connector contract

- Allow only official Zoom API hosts; cross-host redirects fail closed.
- Use PKCE, state verification, exact redirect URI, and minimal read-only recording scopes. Admin/write scopes fail configuration readiness.
- No browser scraping or arbitrary URL fetch.
- Apply connect, read, total elapsed, byte, redirect, and bounded-retry budgets.
- HTTP 429 uses bounded backoff and ends visibly when the request budget is exhausted.
- Downloaded bytes must pass size, content, MP4 signature, FFprobe, and optional SHA-256 validation before entering the existing pipeline.
- The current local-only mode remains fully functional when Zoom is disabled.

## Child backlog items

| ID | Child | Priority | Dependencies | Deliverable |
|---|---|---:|---|---|
| STS-105 | Epic tracking plus architecture/risk/eval updates | Critical | None | Approved scope and traceability |
| STS-106 | Strict CSV/XLSX manifest parser and preview API | Critical | STS-105 | Validated sanitized import plan |
| STS-107 | Prompt and Windows Credential Locker secret providers | Critical | STS-106 | Secret references without persistence |
| STS-108 | Protected ZIP/7z security spike and extraction adapter | Critical | STS-107 | Bounded decrypted MP4 intake |
| STS-109 | Zoom OAuth PKCE and recording-download connector | High | STS-106, STS-107 | Optional bounded remote acquisition |
| STS-110 | MSIX versus WiX/MSI spike and signed installer | High | STS-105 | Intune and Configuration Manager deployment |
| STS-111 | Docker qualification image and container gates | Medium | STS-106 | Reproducible local/CI tests |
| STS-112 | Codespaces devcontainer with synthetic-only policy | Medium | STS-111 | One-command remote test environment |
| STS-113 | Manifest/connector UI and accessibility fast follow | High | STS-108, STS-109 | Operator-ready bulk workflow |
| STS-114 | Cross-environment release UAT and evidence | Critical | STS-108 through STS-113 | Conditional pilot decision |

Sequence foundation and secret handling before connectors, connectors before UI polish, and release evidence last. Installer/container work can proceed after the contracts stabilize.

## Deployment decisions

### Windows production path

Run a packaging spike comparing signed MSIX and WiX/MSI against Intune/Configuration Manager support, silent install/repair/upgrade/rollback/uninstall, signature verification, external model and FFmpeg provisioning, hardware-specific Torch selection, directory ACL creation, offline wheelhouse use, and absence of runtime downloads. Record the selected format in an ADR before installer implementation.

### Docker qualification path

Docker is for testing and qualification, not default desktop production. Use a digest-pinned base image, non-root user, read-only root, dropped capabilities, no Docker socket, SBOM, vulnerability scan, read-only synthetic input, dedicated writable output, and Compose secrets rather than credential environment variables.

### Codespaces test path

Use synthetic fixtures and fake credentials only. Do not provision corporate recordings, production credentials, a production Zoom app, or the full model. Run lint, compile, unit, integration, mocked Zoom, manifest, archive-adversarial, and headless browser tests without automatically public ports. Run real Whisper, Credential Locker, installer, and Windows filesystem acceptance on a managed Windows runner.

## UI/UX fast follow

STS-113 delivers a manifest template, CSV/XLSX file picker and drag/drop, sanitized 25-row preview, per-row readiness/status groups, OAuth connect/disconnect, nonpersistent password prompts, retry/resume without duplicate outputs, keyboard operation, named controls, focus restoration, screen-reader announcements, reduced motion, 200% zoom, and no overflow at 375/768/1440 pixels. Security and ingestion foundation are not delayed for polish.

## Acceptance criteria

1. A valid 25-row CSV and equivalent XLSX normalize to identical plans.
2. Every prohibited workbook feature returns a stable reason code before secret resolution.
3. Password/token canaries produce zero matches across persisted files, logs, process arguments, errors, screenshots, and evidence.
4. Archive traversal, links, nesting, bombs, excess entries, wrong password, and timeout fixtures fail closed with no extracted residue.
5. Zoom OAuth verifies PKCE/state and accepts only the recorded minimal read scopes.
6. Redirect, SSRF, oversize, invalid MP4, expired/revoked token, timeout, and 429 paths reach deterministic terminal results.
7. Existing upload/folder workflows pass unchanged with every connector disabled.
8. Resume by batch ID never retranscribes a completed row or overwrites output.
9. Deletion removes managed manifest, downloaded/decrypted source, extraction workspace, transcript, and analysis; external exports remain outside managed deletion.
10. Docker/Codespaces use synthetic data only and contain no production secret.
11. The signed installer passes clean install, upgrade, rollback, repair, uninstall, and signature checks on managed Windows images.
12. UI passes keyboard, screen-reader, 200% zoom, responsive, recovery, and secret-display checks.
13. L1-L3 architecture, ADRs, risk register, eval catalog, SBOM, provenance, and UAT evidence are updated.
14. Pilot status remains conditional until security, privacy/records, and accessibility owners approve the new boundaries.

## Testing plan

| Layer | Coverage | Minimum additions |
|---|---|---:|
| Unit | CSV/XLSX schemas, normalization, secret refs, retries, IDs | 30 |
| Integration | Preview/execute, secret lifecycle, archive, mocked Zoom, deletion/resume | 18 |
| Security | Formula/external-link files, traversal, bombs, redirects, token leakage | 15 |
| End-to-end | Local archive, mocked Zoom, UI preview/recovery, connector-disabled regression | 8 |
| Packaging | Install, upgrade, repair, rollback, uninstall, signature | 6 |
| Environment | Docker, Codespaces, Windows real-model smoke | 3 suites |

Manifest preview must complete within two seconds for a 5 MiB/25-row workbook on the reference endpoint. Measure manual versus manifest-assisted operator time in UAT; no productivity claim is made before that measurement.

## Rollback

- Ship manifest, archive, and Zoom paths disabled behind separate feature flags.
- Disabling a connector leaves existing completed jobs readable.
- Revoke and locally delete OAuth authorization.
- Keep manifest schemas additive and versioned.
- Retain the previous signed package for managed rollback.
- Reverting this epic leaves existing folder batches and schema `1.0` records operational.

## Files reference

| File | Intended change |
|---|---|
| `src/secure_transcribe/models.py` | Versioned import-plan, source, and connector contracts |
| `src/secure_transcribe/config.py` | Disabled-by-default feature flags and budgets |
| `src/secure_transcribe/app.py` | Preview/execute and Zoom authorization routes |
| `src/secure_transcribe/batch.py` | Execute validated plan through existing jobs |
| `src/secure_transcribe/storage.py` | Sanitized plan provenance and deletion |
| `src/secure_transcribe/manifest.py` | Strict CSV/XLSX parser |
| `src/secure_transcribe/secrets.py` | Prompt and Windows credential adapters |
| `src/secure_transcribe/archive.py` | Bounded protected-archive adapter |
| `src/secure_transcribe/zoom.py` | OAuth and download adapter |
| `src/secure_transcribe/static/*` | STS-113 fast-follow workflow |
| `.devcontainer/*`, `Dockerfile`, `compose.yaml` | Synthetic test environments |
| `installer/*` | Packaging spike and selected signed installer |
| `architecture/*`, `evals/*`, `governance/*`, `evidence/*` | Traceability and release evidence |

## New risks

- R-14: password/token disclosure.
- R-15: OAuth overreach, SSRF, redirects, rate limits, and remote content trust.
- R-16: workbook/archive parser exploitation and decompression exhaustion.
- R-17: installer/container supply-chain or privilege expansion.
- R-18: corporate data or secrets entering Codespaces or test evidence.
- R-19: UI hides row failures, authorization state, or external-copy consequences.

## Out of scope

- Legacy `.xls`, macro-enabled workbooks, and DRM-encrypted MP4.
- Zoom meeting creation, scheduling, recording administration, browser scraping, webhooks, and account-wide server-to-server access.
- Public/LAN container service.
- Corporate recordings or real credentials in Codespaces.
- Raising the 25-file limit.
- Automatic DLP, records classification, backup deletion, compliance certification, or generative transcript analysis.
