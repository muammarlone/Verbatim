# Architecture Runway

Architecture runway represents planned structural investments that enable near-term features without requiring an emergency refactor. These are not speculative abstractions — each item below is tied to a concrete backlog story and a named gate. No runway item is implemented ahead of its linked story; this document is a decision record, not a license to build.

**Principal architect judgment:** The current architecture is adequate for Phase 1 (trust baseline) work. Phase 2 and Phase 3 features require the runway investments described below. None may be implemented until the relevant Phase 1 gates have accountable owners and accepted plans.

---

## Runway item R-01 — Per-format media validation abstraction

**Enables:** STS-118 (done), future format additions, Phase 3 connector intake  
**Linked gate:** QG-01, QG-06  
**Status:** Partially realized (STS-118 complete)

`security.py` now contains `validate_media_signature` with per-format dispatch (MP4/M4A, WAV, MP3, FLAC, OGG; AAC/WMA deferred to FFprobe). The current implementation is adequate for supported formats. Future additions (e.g., MKV, WebM) follow the same dispatch pattern without touching upstream validation code.

**Remaining work:** None required before Phase 1 gates. If additional container formats are added, extend `SUPPORTED_MEDIA_EXTENSIONS` and `validate_media_signature` following the existing pattern.

---

## Runway item R-02 — Whisper confidence field pipeline

**Enables:** STS-118 (done), STS-104 (domain evaluation), STS-101 (diarization)  
**Linked gate:** QG-01  
**Status:** Realized (STS-118 complete)

`TranscriptSegment.avg_logprob` and `TranscriptSegment.no_speech_prob` are now captured per segment and surfaced in the UI as a color-coded confidence badge. The JSON export includes these fields. Domain evaluation (QG-01) can use these signals to stratify accuracy by confidence band.

**Remaining work:** QG-01 requires a human-approved threshold policy — the signals are available, but interpretation policy is not set. No additional code is needed before QG-01 enters evaluation.

---

## Runway item R-03 — Windows Credential Locker `secret_ref` resolution contract

**Enables:** STS-107, STS-108, STS-121, STS-122  
**Linked gate:** QG-07  
**Status:** Not started — blocked on Phase 1 gate clearance

The CSV manifest schema already supports a `secret_ref` column (STS-106). The resolution contract (STS-107) defines how a named Credential Locker entry is retrieved at runtime, used once, and discarded without logging. This contract is a prerequisite for every connector that needs a password or token.

**Pre-implementation requirements:**
- STS-107 threat model approved by security lead
- Secret lifecycle (provisioning, rotation, revocation, audit trail) documented and approved
- No plaintext credential in logs, audit events, or process memory beyond the immediate use window

**Blocking condition:** Must not begin until Phase 1 trust gates (QG-01 through QG-06) have accountable owners and accepted plans.

---

## Runway item R-04 — Platform connector module structure (ADR-006)

**Enables:** STS-121 (Teams), STS-122 (Zoom), STS-108 (ZIP/7z)  
**Linked gate:** QG-07  
**Status:** Architecture defined (ADR-006); implementation not started

ADR-006 defines the connector isolation model: each connector is a separate Python module with its own feature flag, ADR, and threat model. The download-then-process-then-delete pattern reuses the existing service pipeline (C3/C5/C6 in L2 terms). No connector code exists today.

**Module layout when implemented:**
```
src/secure_transcribe/connectors/
    __init__.py          # empty; no connector in hot path
    teams.py             # STS-121; gated by STS_TEAMS_CONNECTOR_ENABLED
    zoom.py              # STS-122; gated by STS_ZOOM_CONNECTOR_ENABLED
    archive.py           # STS-108; gated by STS_PROTECTED_ARCHIVE_ENABLED
```

Each connector module:
- Imports only from `config`, `security`, `storage`, `errors`
- Never imports from `app`, `service`, `batch`, `manifest`, or other connectors
- Has its own test file covering: download success, download failure, oversized response, hostile redirect, SSRF, cleanup on failure, Credential Locker integration

**Sequencing:**
1. Phase 3A: `archive.py` (STS-108) + `teams.py` (STS-121) — both within corporate trust boundary
2. Phase 3B: `zoom.py` (STS-122) — requires external vendor approval (Zoom Marketplace)

**Blocking condition:** All three connectors are blocked until ADR-006 per-platform pre-implementation checklist is complete. Do not implement any connector before Phase 1 gate clearance.

---

## Runway item R-05 — Sensitive entity detection pipeline (BHI/BII/PHI/PII)

**Enables:** STS-119 (entity flagging), STS-120 (redaction export)  
**Linked gate:** QG-01 (accuracy), QG-05 (records governance)  
**Status:** Not started — blocked on privacy lead approval and NLP approach review

Transcripts may contain protected health information (PHI), personally identifiable information (PII), biometric health information (BHI), or biometric identifier information (BII). STS-119 adds a locally-running NLP pass that identifies candidate spans without a cloud call.

**Architecture constraints:**
- Detection must run locally on transcript text — no cloud NLP API
- Output is a flag report co-exported with the transcript; it does not modify the source transcript
- False-positive and threshold trade-offs must be disclosed in the UI
- Privacy threat model and NLP approach must be reviewed and approved by the privacy lead before any implementation

**Blocking condition:** Privacy lead must approve NLP model choice, local execution approach, and output format before STS-119 begins. STS-120 (redaction) may not begin before STS-119 is complete.

---

## Runway item R-06 — Signed deployment and endpoint qualification (ADR-005)

**Enables:** QG-02 exit (IT-signed package), pilot authorization  
**Linked gate:** QG-02  
**Status:** Repository preparation complete (STS-117); IT qualification not started

`sbom/` contains the transitive dependency lock, CycloneDX SBOM, vulnerability disposition, and hash manifest (with null endpoint fields). `scripts/install/` contains installer stubs with the `VERBATIM_INSTALLER_PRODUCTION_READY` guard. ADR-005 documents the MSIX vs WiX/MSI decision.

**IT must complete:**
- Offline wheelhouse build on managed Windows image
- Clean-machine install, repair, upgrade, uninstall, rollback tests
- Signed package with attested hashes for FFmpeg, model, and all wheels
- `binary_sha256` and `file_sha256` fields in `sbom/hash-manifest.json` populated from the qualified endpoint — not from development machine

**Security constraint:** The `VERBATIM_INSTALLER_PRODUCTION_READY` guard must not be self-assigned. Only IT's signed package may set this value.

---

## Summary table

| ID | Runway item | Phase | Status | Blocking story |
|---|---|---|---|---|
| R-01 | Per-format media validation | Phase 1 | Realized (STS-118 done) | — |
| R-02 | Whisper confidence field pipeline | Phase 1 | Realized (STS-118 done) | QG-01 threshold policy |
| R-03 | Credential Locker `secret_ref` contract | Phase 3 | Not started | STS-107 threat model, Phase 1 gate clearance |
| R-04 | Connector module structure (ADR-006) | Phase 3 | Architecture defined | Phase 1 gate clearance, per-platform ADRs |
| R-05 | BHI/BII/PHI/PII entity detection | Phase 2+ | Not started | Privacy lead approval, NLP approach review |
| R-06 | Signed deployment and endpoint qualification | Phase 2 | Prep complete (STS-117) | IT qualification |

---

## What this runway does NOT authorize

- Implementing any connector before ADR-006 per-platform checklist is complete
- Populating `sbom/hash-manifest.json` hashes from a development machine
- Running Credential Locker resolution before STS-107 threat model is approved
- Starting BHI/BII/PHI/PII detection before privacy lead approval
- Claiming pilot-readiness while QG-01 through QG-06 remain blocked
