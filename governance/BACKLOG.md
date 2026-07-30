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
| STS-011 | Reviewers can inspect L1-L3 architecture and deterministically detect implementation or evidence drift. | Three architecture definitions and rendered/editable diagrams; versioned 19-gate catalog; fail-closed validator and negative controls | R-09, R-13 | done |
| STS-101 | Add speaker diarization with measured evaluation. | Held-out diarization set and subgroup report | R-05 | not_started |
| STS-102 | Add transcript correction with version history. | Edit/revision tests and audit replay | R-05, R-07 | not_started |
| STS-103 | Add OS-backed user authentication and encrypted application storage. | Threat model, pen test, recovery drill | R-01, R-08 | not_started |
| STS-104 | Evaluate language/domain accuracy and confidence presentation. | Sealed multilingual/domain test set | R-05 | not_started |
| STS-105 | Govern the secure protected-recording intake epic and keep architecture, risks, evaluations, and decisions synchronized. | Approved epic and issue #1; updated L1-L3 definitions/diagrams, ADR-004, risk register, 21-gate catalog/report, and evidence index | R-14, R-15, R-16, R-17, R-18, R-19 | done |
| STS-106 | As an authorized operator, I can preview a strict CSV/XLSX manifest without exposing credentials or importing unsupported content. | 87-test regression; hostile workbook cases; 25-row/5 MiB caps; versioned reason codes; sanitized memory-only API; direct dependency audit | R-14, R-16 | done |
| STS-107 | As an authorized operator, I can resolve manifest `secret_ref` values through prompt or Windows Credential Locker without logging or persisting plaintext secrets. | Provider contract tests, redacted audit tests, lifecycle/revocation tests, 20-reference cap | R-14 | not_started |
| STS-108 | As an authorized operator, I can extract a bounded password-protected ZIP/7z recording through a qualified adapter. | Security spike, traversal/link/bomb corpus, cleanup and timeout tests, approved adapter ADR | R-14, R-16 | not_started |
| STS-109 | As an authorized Zoom user, I can retrieve an authorized recording through user OAuth with PKCE and bounded download controls. | Scope/host allowlist tests, OAuth expiry/revocation tests, rate-limit and redirect tests, synthetic connector fixtures | R-14, R-15 | not_started |
| STS-110 | IT can deploy, repair, upgrade, and uninstall a signed Windows package using Intune or Configuration Manager. | MSIX versus WiX/MSI ADR, signed-package verification, clean-machine install/upgrade/uninstall evidence | R-17 | not_started |
| STS-111 | Developers can run a loopback-only Docker qualification image with mounted data and injected secrets. | Image scan/SBOM, non-root and private-port tests, synthetic end-to-end run | R-17, R-18 | not_started |
| STS-112 | Contributors can use a Codespaces devcontainer for synthetic/mock testing without production data or credentials. | Devcontainer policy checks, fake-secret fixtures, private-port verification, documented stop gate | R-18 | not_started |
| STS-113 | Operators receive accessible manifest preview, per-row recovery, authentication, and external-copy guidance. | Keyboard/screen-reader/contrast matrix, row-state usability tests, error-recovery UAT | R-14, R-15, R-19 | not_started |
| STS-114 | Release reviewers can reproduce cross-environment security, regression, installer, and connector evidence before pilot. | Windows runner, Docker, Codespaces, offline regression, negative controls, signed evidence manifest | R-14, R-15, R-16, R-17, R-18, R-19 | not_started |
