# Audit and Readiness Report

## Decision

**Proceed with conditions** for a controlled, non-production internal demonstration using synthetic or explicitly authorized low-risk recordings on a managed endpoint.

## Evidence reviewed (updated 2026-07-30)

- 23 deterministic architecture gates passed across the L1 system boundary, L2 runtime/dependency map, L3 component/contracts, manifest-preview controls, and documentation, product, roadmap, and evidence traceability. Negative-control tests confirm forbidden network imports, unapproved dependency edges, duplicate gate IDs, and unsupported promotion claims fail closed.
- 256 automated tests passed (16 skipped on unfilled environment evidence placeholders) with 83% measured Python branch coverage. Additions since initial readiness: devcontainer policy (STS-112), Docker qualification image (STS-111), transcript correction/revision API (STS-102), accessibility contract matrix (STS-113), WER accuracy eval harness with synthetic fixtures (STS-104), cross-environment evidence structure (STS-114). Coverage held stable.
- The versioned eight-gate principal-architect roadmap validates with `promotion_ready=false`; QG-01 through QG-06 remain explicit corporate-pilot blockers with owner roles, exit criteria, evidence, and next actions.
- Four fresh Chromium cases passed at 375, 768, and 1440 px in light and dark presentation with keyboard tab navigation, skip-link focus, named dialogs, no horizontal overflow, no console errors, required security headers, and no unexpected network requests.
- The direct-pin CycloneDX inventory matches `requirements.txt`, and the direct-pin advisory report contains no known vulnerabilities. Full transitive and signed-installer qualification remain open.
- Ruff, Python compilation, JavaScript syntax, PowerShell parsing, and wheel packaging checks passed.
- Real 9.193-second synthetic MP4 completed in 16.18 seconds through the bounded API worker.
- Expected 17-word English fixture was reproduced exactly in two segments.
- Model SHA-256, source SHA-256 presence, duration, schema, job ID, and analysis method were recorded.
- Playwright passed desktop/tablet/mobile checks with zero console errors and zero horizontal overflow.
- Screenshot review detected and drove a fix for stale `[hidden]` panels; the rerun passed.
- A narrated 114.52-second end-to-end recording captured authorization, real local processing, transcript review, deterministic analysis, JSON export, readiness, and deletion with zero browser console errors.
- The recording preserves the measured 80.618-second processing wall time in its evidence report and visibly labels the only accelerated interval at 12×.
- A real two-file local batch completed in 25.34 seconds and wrote the selected formats plus a manifest with two exact synthetic transcript matches.
- The 62.2-second narrated batch recording captured folder selection, all five formats, two local jobs, per-file review, and managed-copy cleanup with zero console errors.
- The batch evidence preserves the measured 39.095-second processing wall time and visibly labels the only accelerated interval at 16×.

- A near-limit synthetic XLSX parser test completed in 0.25 seconds including fixture handling against the two-second parser gate; no reference-endpoint/UI throughput claim is made.
- The isolated `python-multipart==0.0.31` overlay passed the then-current 87-test suite, the wheel build passed, and a direct pinned-dependency audit reported no known vulnerabilities. Full transitive audit remains blocked by `openai-whisper` build metadata in the audit tool.

## Controls passed

Loopback binding, trusted host, request token, consent gate, upload/media validation (MP4/M4A/MP3/WAV/AAC/FLAC/OGG/WMA with per-format magic-byte check), UUID path isolation, atomic state writes, bounded media tools, killable transcription timeout, one-job concurrency, model provenance, content-free audit events, temporary audio cleanup, explicit deletion, retention sweep, schema validation, safe error states, bounded deterministic analysis, batch-root containment, traversal/link blocking, non-recursive scans, file/byte caps, per-file failure isolation, output collision rejection, no-overwrite exports, per-segment Whisper confidence fields (avg_logprob, no_speech_prob), default-off manifest routing, bounded hostile-workbook rejection, secret-reference redaction, expiring memory plans, architecture dependency boundaries, semantic/contrast/keyboard regressions, cross-origin response protections, roadmap promotion controls, and claim-to-regression traceability.

## Conditions before any corporate pilot

1. Security owner approves FFmpeg, Python/Torch/Whisper packages, model artifact, endpoint ACL, encryption, and egress policy.
2. Privacy/records owner approves recording authority language, retention, deletion, backup, and export handling.
3. Pilot owner defines a representative evaluation set and human transcript-review workflow.
4. Accessibility and penetration testing are completed for the intended deployment profile.
5. Incident, rollback, storage-capacity, and model-update procedures have named owners.
6. IT and records owners approve the batch-workspace root, output-folder ACL/DLP, retention, and cleanup boundary for external copies.
7. Manifest intake remains disabled outside controlled contract testing until credential, archive/Zoom, UI/accessibility, installer, and cross-environment gates are approved.

## Not approved

Manifest execution, protected-archive extraction, Zoom retrieval, production deployment, regulated workflows, legal-record generation, multi-user service, unsupervised analysis, general accuracy/quality claims, ROI claims, or compliance claims.
