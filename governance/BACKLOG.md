# Traceable Backlog

| ID | Story | Acceptance evidence | Linked risk | Status |
|---|---|---|---|---|
| STS-001 | As an authorized user, I can import a bounded MP4 without path injection. | API/security tests; `INVALID_MP4_SIGNATURE`; upload cap | R-01, R-02 | done |
| STS-002 | I can transcribe with a provisioned local model and no network call. | Synthetic MP4 exact transcript; model SHA-256 | R-03, R-04 | done |
| STS-003 | I can review and search time-linked passages beside the video. | Playwright screenshots and two rendered fixture segments | R-05 | done |
| STS-004 | I can inspect bounded, clearly labeled analysis. | Deterministic analysis tests and limitations UI | R-06 | done |
| STS-005 | I can export portable transcript/evidence formats. | TXT/SRT/VTT/MD/JSON tests; API export `200` | R-07 | done |
| STS-006 | I can delete source and derived artifacts. | API deletion-propagation test | R-08 | done |
| STS-007 | IT can configure retention, storage, model, and budgets. | `.env.example`, README, system readiness | R-09 | done |
| STS-008 | A reviewer can inspect a reproducible recorded synthetic workflow from consent through deletion. | Narrated MP4, timing report, exported JSON, console log, deletion audit | R-05, R-06, R-08, R-10 | done |
| STS-009 | As an authorized operator, I can transcribe a bounded MP4 input folder into selected text formats in an approved output folder. | Batch API/UI tests, real two-file smoke, manifest, responsive UAT, narrated cleanup demo | R-04, R-05, R-07, R-08, R-11 | done |
| STS-010 | Batch and upload failures stop safely without partial output, silent monitor loss, or active-work deletion races. | Pre-parser request cap, atomic-output and monitor failure injection, stable validation envelope, active/batch-owned deletion regressions | R-04, R-08, R-12 | done |
| STS-101 | Add speaker diarization with measured evaluation. | Held-out diarization set and subgroup report | R-05 | not_started |
| STS-102 | Add transcript correction with version history. | Edit/revision tests and audit replay | R-05, R-07 | not_started |
| STS-103 | Add OS-backed user authentication and encrypted application storage. | Threat model, pen test, recovery drill | R-01, R-08 | not_started |
| STS-104 | Evaluate language/domain accuracy and confidence presentation. | Sealed multilingual/domain test set | R-05 | not_started |
