# Verbatim Secure Transcription Studio

Verbatim is a local-first utility for turning MP4 recordings into searchable, time-linked transcripts. It runs on `127.0.0.1`, uses an on-device Whisper model, calls no cloud API, and gives the operator explicit export and deletion controls.

![Transcript review](evidence/screenshots/review-desktop.png)

## Verified MVP capability

- Import one MP4 or run a bounded, non-recursive folder batch after authorization confirmation.
- Validate the extension, MIME type, MP4 signature, duration, and audio track.
- Extract 16 kHz mono audio with bounded FFmpeg/FFprobe subprocesses.
- Transcribe with a locally provisioned Whisper model in a killable, time-bounded worker.
- Search time-linked segments and seek the local video from a transcript passage.
- Review deterministic key moments, action-keyword matches, questions, terms, pace, and counts.
- Export TXT, SRT, VTT, Markdown, or a JSON evidence package.
- Write selected formats for each batch file into an approved output folder without overwriting existing files.
- Delete the source, working audio, transcript, and analysis for a job.
- When explicitly enabled by IT, validate and sanitize a bounded CSV/XLSX recording manifest into a 30-minute process-memory preview without resolving credentials or acquiring media.

The synthetic acceptance fixture passed the real FFmpeg + Whisper path on July 29, 2026. The intended 17-word transcript was reproduced exactly in 16.18 seconds using the local `base.pt` artifact recorded in the evidence packet. This is one controlled fixture, not a general accuracy claim.

## Recorded demonstration

[Watch the grounded product explainer](evidence/explainer/verbatim-grounded-product-explainer.mp4)
for a concise tour of current capabilities, usage, strengths, trade-offs, unavailable
features, and pilot gates. The [user manual](docs/USER_MANUAL.md) provides task-by-task
instructions, while [features and limitations](docs/FEATURES_AND_LIMITATIONS.md) is the
claim-boundary reference.

[Watch the narrated end-to-end demo](evidence/demo/verbatim-end-to-end-demo.mp4) or open the [demo evidence index](evidence/demo/README.md). The 114.52-second recording shows authorization, real local processing, transcript search, deterministic analysis, JSON export, readiness, and permanent deletion using synthetic data. Screen recording increased the measured processing time to 80.618 seconds, so only the middle of that wait is played at 12× with an on-screen disclosure.

[Watch the folder-to-folder batch demo](evidence/batch-demo/verbatim-batch-end-to-end-demo.mp4) or inspect its [verification record](evidence/batch-demo/README.md). The 62.2-second recording processes two synthetic MP4s into all five formats, reviews a generated transcript, and removes managed copies while preserving the original input and requested outputs.

## Folder batches

Set `STS_BATCH_ROOT` to an IT-approved workspace. Create an input folder inside that root, place MP4 files directly inside it, and use **Folder batch** in the UI. Input and output values are relative to the configured root; nested scanning, path traversal, symbolic links/junctions, and overwriting existing outputs are blocked.

## Manifest preview foundation

STS-106 provides a backend-only, disabled-by-default preview route for the versioned seven-column CSV/XLSX contract in [the protected-recording epic](governance/EPIC_SECURE_PROTECTED_RECORDING_INTAKE.md). It validates at most 25 rows and returns a credential-target-redacted, expiring plan. It does not execute a plan, unlock an archive, contact Zoom, create a transcription job, or provide the fast-follow UI. Keep it disabled outside controlled contract testing until STS-107 through STS-114 pass their gates.

## Quick start

Requirements: Windows, Python 3.11+, an IT-approved FFmpeg installation, and an approved Whisper `.pt` model stored locally.

```powershell
cd "C:\Claude Cowork\JHU Course\mini_projects\07_secure_transcription_studio"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:STS_MODEL_PATH = "C:\approved\models\base.pt"
$env:STS_DATA_DIR = "C:\approved\VerbatimData"
$env:STS_BATCH_ROOT = "C:\approved\VerbatimBatchWorkspace"
.\Start-Verbatim.ps1
```

Open `http://127.0.0.1:8765` if the browser does not open automatically.

For an air-gapped installation, have IT create an approved wheelhouse on a connected build machine, scan it, and install with:

```powershell
python -m pip install --no-index --find-links .\wheelhouse -r requirements.txt -c constraints.verified-windows.txt
```

Torch builds are hardware-specific. The organization should select and approve its CPU or GPU package; this repository does not download or silently replace model files.

## Configuration

Copy values from `.env.example` into the service account or launcher environment. Defaults are deliberately bounded:

| Setting | Default | Purpose |
|---|---:|---|
| `STS_MAX_UPLOAD_BYTES` | 2 GiB | Upload budget |
| `STS_BATCH_ROOT` | `<data>/batch-workspace` | Approved folder-to-folder boundary |
| `STS_MAX_BATCH_FILES` | 25 | MP4s per non-recursive batch |
| `STS_MAX_BATCH_BYTES` | 10 GiB | Combined batch input budget |
| `STS_MAX_MEDIA_SECONDS` | 4 hours | Media-duration budget |
| `STS_FFMPEG_TIMEOUT_SECONDS` | 2 hours | Media-tool elapsed budget |
| `STS_TRANSCRIPTION_TIMEOUT_SECONDS` | 2 hours | Killable Whisper elapsed budget |
| `STS_RETENTION_DAYS` | 7 days | Startup retention sweep |
| `STS_MAX_JOBS` | 100 | Local storage/job cap |
| `STS_MANIFEST_INTAKE_ENABLED` | `false` | Enables the bounded backend preview contract only |
| `STS_PROTECTED_ARCHIVE_ENABLED` | `false` | Reserved stop gate; no archive implementation yet |
| `STS_ZOOM_CONNECTOR_ENABLED` | `false` | Reserved stop gate; no Zoom implementation yet |
| `STS_MAX_MANIFEST_BYTES` | 5 MiB | CSV/XLSX byte cap; configuration may only lower it |
| `STS_IMPORT_PLAN_TTL_SECONDS` | 30 minutes | Process-memory plan lifetime; configuration may only lower it |
| `STS_MAX_IMPORT_PLANS` | 100 | Process-memory plan capacity |

The UI shows system readiness before enabling transcription. Model downloads are never attempted; a missing model is a visible blocked state.

## Test and verification

```powershell
python scripts\validate_architecture.py
python scripts\validate_quality_gates.py --write-report
python scripts\validate_product_evidence.py
python scripts\run_browser_quality_uat.py
python -m pytest
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
node --check src\secure_transcribe\static\app.js
```

Current evidence: 23/23 architecture gates and 92 tests passed with 84% measured Python coverage including branch tracking; Python compilation, Ruff, JavaScript syntax, PowerShell parsing, JSON parsing, and wheel packaging passed. Four responsive light/dark Chromium quality cases passed, the direct pinned-dependency audit found no known vulnerabilities, and the eight-gate principal-architect roadmap blocks corporate-pilot promotion on six open gates. Existing real-media evidence continues to cover the unchanged upload/folder workflows; manifest UI and execution are not claimed. See [evidence/README.md](evidence/README.md).

## Security and claim boundary

This MVP is designed for single-user operation on a managed endpoint. It is not a compliance certification, multi-user server, legal-records system, or proof of transcription accuracy across accents, languages, noise conditions, or domains. Anyone with the same operating-system account and data or batch-workspace access may read stored files. Exported batch files are external copies and remain until the operator or records process removes them. Use full-disk encryption, approved directory ACLs, endpoint protection, and the organization's retention policy.

See [SECURITY.md](SECURITY.md), [ARCHITECTURE.md](ARCHITECTURE.md), the [principal-architect quality roadmap](governance/QUALITY_ROADMAP.md), the [readiness decision](governance/READINESS_REPORT.md), and the [Claude Code execution handoff](governance/CLAUDE_CODE_HANDOFF.md) before a pilot or further implementation.

The architecture package includes [L1 system context](architecture/L1_SYSTEM_CONTEXT.md), [L2 runtime containers](architecture/L2_CONTAINER_ARCHITECTURE.md), [L3 implementation components](architecture/L3_COMPONENT_ARCHITECTURE.md), editable/rendered diagrams, and a deterministic 23-gate [evaluation catalog](evals/architecture-evals.json).
