# Verbatim Secure Transcription Studio — Comprehensive Product Roadmap

*Version 1.1 — 2026-07-30. Owned by Product Owner and Principal Architect.*
*Gate authority: `evals/quality-roadmap.json`. Story authority: `governance/BACKLOG.md`.*
*Owner assignments: `governance/OWNER_ASSIGNMENT_REGISTER.md`.*
*Audit principle: `governance/AUDIT_SINGLE_PURPOSE_PRINCIPLE.md`.*

**Role naming note:** Generic labels ("program sponsor", "domain evaluation lead", etc.) are
replaced throughout this document with proper functional titles. See `OWNER_ASSIGNMENT_REGISTER.md`
for assignments and Phase 0 completion status.

---

## Executive decision

**Target:** Controlled corporate pilot on a qualified managed Windows endpoint.
**Current decision:** `proceed_with_conditions` — synthetic demonstration approved; corporate pilot blocked.
**Promotion control:** `promotion_ready=false`. Requires all promotion-blocking gates to pass with reproducible evidence.

---

## Baseline: what is complete (2026-07-30)

| Area | State |
|------|-------|
| Core transcription and review (STS-001–006) | done |
| Folder-batch processing (STS-009, STS-010) | done |
| Multi-format audio (STS-118) | done |
| Transcript corrections and revision history (STS-102) | done |
| Architecture gates and validators (STS-011, QG-08) | done — QG-08 passed |
| Manifest preview contract (STS-105, STS-106) | done — disabled by default |
| Accessibility matrix (STS-113) | done — automated; manual open |
| Cross-env regression structure (STS-114) | done |
| Supply chain: SBOM, lock, hash manifest (STS-117) | done — IT qualification open |
| Docker qualification image (STS-111) | done |
| Codespaces dev environment (STS-112) | done |
| Installer stubs (STS-110 partial) | done — signing open |
| Eval harness — 46 synthetic cases (STS-104) | done — real dataset open |
| Grounded explainer and user manual (STS-115) | done |
| Principal architect quality roadmap (STS-116) | done |
| Two Principal QA Analyst roles (PQAPS, PQAFE) | chartered — unstaffed |
| Audit Single-Purpose Principle (ADR-007) | accepted — not implemented |
| Automated tests | 465 passing, 86% branch coverage |

---

## What blocks the pilot (6 gates)

| Gate | Title | State | Hard dependency |
|------|-------|-------|----------------|
| QG-01 | Transcription quality | blocked | Sealed real-domain eval set + human reviewer acceptance |
| QG-02 | Signed installer and supply chain | partial | DevSecOps Engineer: offline wheelhouse, signed package, clean-machine matrix |
| QG-03 | OS identity, ACL, encryption, pen test | blocked | Managed endpoint + named Information Security Officer |
| QG-04 | Accessibility and application security | partial | Manual screen-reader run + independent pen test report (zero unresolved critical/high) |
| QG-05 | Export/retention governance | partial | Records and privacy owner: DLP, training, deletion drills; audit store principle sign-off |
| QG-06 | Performance and recovery matrix | partial | Managed endpoint: P50/P95 profiling, full-disk and interruption drills |

**QG-08** (truthful evidence): passed. **QG-07** (connectors): not a local-only pilot blocker.

---

## Phase 0: Role Assignment and Governance Sign-offs

**Duration:** Weeks 0–3 (can run in parallel with Phase 1A)
**Gate impact:** Unblocks Phase 1B. No gate can produce accepted evidence without a named, accountable owner.
**Status as of 2026-07-30:** AI-fillable and product-owner-fillable slots resolved. See `OWNER_ASSIGNMENT_REGISTER.md`.

| Action | Assigned role | Status |
|--------|--------------|--------|
| Product Owner names and authorizes the program | Product Owner (muammarlone@gmail.com) | ✓ done |
| Name Principal Architect | Principal Architect (AI) | ✓ done |
| Name Principal Security and Privacy Architect | Principal Security and Privacy Architect (AI) | ✓ done |
| Name Principal Release Engineer (QG-08) | Principal Release Engineer (AI) | ✓ done |
| Staff Principal QA Engineer — Privacy and Security (PQAPS) | Principal QA Engineer — Privacy and Security (AI) | ✓ done |
| Staff Principal QA Engineer — Functionality and E2E (PQAFE) | Principal QA Engineer — Functionality and E2E (AI) | ✓ done |
| Name AI Quality and Evaluation Engineer (QG-01) | AI Quality and Evaluation Engineer (AI) | ✓ done — real-domain eval needs human domain SME |
| Data Protection Officer signs `AUDIT_SINGLE_PURPOSE_PRINCIPLE.md` | Data Protection Officer (Product Owner, course context) | ✓ signed 2026-07-30 |
| Principal Security and Privacy Architect countersigns principle | Principal Security and Privacy Architect (AI) | ✓ signed 2026-07-30 |
| DevSecOps / Release Engineer named (QG-02) | DevSecOps Engineer | PENDING — human with signing certificate required |
| Information Security Officer named (QG-03) | Information Security Officer | PENDING — human with managed endpoint access required |
| Product Security and Accessibility Lead named (QG-04) | Product Security and Accessibility Lead | PENDING — human for screen-reader testing required |
| IT Systems Engineer named (QG-06) | IT Systems Engineer | PENDING — human with hardware access required |
| Service identity and storage policy defined | Information Security Officer | PENDING — depends on above |

**Phase 0 conclusion:** All AI-fillable and product-owner-fillable roles assigned. Remaining PENDING roles require human organizational capacity and do not block Phase 1A. **Phase 1A is unblocked.**

---

## Phase 1A: Repository-Deliverable Work

**Duration:** Weeks 1–6 (runs in parallel with Phase 0; does not require managed endpoint)
**Gate impact:** Provides implementation for QG-03 (auth) and QG-05 (audit store); PQAPS validates both.

### STS-123 — Encrypted Audit Store and Transcript Derivation Tree

**Dependencies:** Records/privacy owner + principal security architect sign `AUDIT_SINGLE_PURPOSE_PRINCIPLE.md` (Phase 0). No code merged to `main` before both signatures are recorded.

| Story | Deliverable | Acceptance check |
|-------|-------------|-----------------|
| STS-123 | `AuditStore` class — DPAPI-encrypted append-only NDJSON per job in `STS_AUDIT_DIR` | Every record carries `purpose:audit_only` + HMAC-SHA-256 tag |
| STS-123 | 8 record types: source, extraction, transcription, segment, revision, export, deletion | Append-only: integration test proves no record mutates after write |
| STS-123 | Content-free: text stored as SHA-256 hash only | Export API negative-control test: zero audit bytes in any export response |
| STS-123 | `STS_AUDIT_MIN_RETENTION_DAYS` floor enforced | Application cannot delete before floor; PQAPS validates |
| STS-123 | `STS_AUDIT_QUERY_ENABLED=false` default | Audit endpoint absent from swagger; not reachable from normal UI |
| STS-123 | Deletion record written after managed-copy deletion | Tree survives job delete — asserted in test |

**PQAPS gate:** Validates HMAC integrity, append-only enforcement, access separation, no-export guard, and retention floor on managed endpoint before QG-03 and QG-05 can close.

### STS-103 — OS-Backed Authentication and Encrypted Storage (Interface)

**Note:** Full delivery requires the managed endpoint (Phase 1B). This phase delivers the interface and stub, so Information Security Officer can slot in the implementation.

| Deliverable | Acceptance check |
|-------------|-----------------|
| Auth interface contract + threat model draft | Information Security Officer reviews before merge |
| Windows Credential Locker integration stub (disabled by default) | Feature flag off; no-op in dev |
| Integration test stubs for recovery, revocation, and failure modes | Tests skipped until endpoint available |

---

## Phase 1B: Trust Baseline — Managed Endpoint Work

**Duration:** Weeks 4–16 (starts after Phase 0 owners are named; runs in parallel tracks)
**Gate impact:** Closes QG-01, QG-02, QG-03, QG-04, QG-05.
**Hard constraint:** Cannot start any track without the named gate owner for that track.

### Track 1 — QG-01: Transcription Quality (Domain Evaluation Lead)

| Step | Owner | Deliverable | Evidence location |
|------|-------|-------------|------------------|
| Define and version the sealed evaluation dataset | AI Quality and Evaluation Engineer | Dataset card: language, domain, noise, speaker coverage; no production recordings | `evidence/eval/dataset-card.json` |
| Run STS-104 eval harness against sealed set | AI Quality and Evaluation Engineer + PQAFE | WER by subgroup (en/es/fr/de × clean/noisy × general/medical/legal/finance) | `evidence/eval/sealed-eval-results.json` |
| Meaning-impact review of consequential errors | Qualified human reviewer | Reviewer acceptance at stated threshold | `evidence/eval/human-review-acceptance.json` |
| Record model hash and dataset version | PQAFE | Pinned model SHA-256; dataset digest | `sbom/hash-manifest.json` (endpoint fields) |

**QG-01 closes when:** Sealed dataset versioned, subgroup WER measures recorded, human reviewer accepts consequential-error threshold.

### Track 2 — QG-02: Signed Installer and Supply Chain (IT Packaging Lead)

| Step | Owner | Deliverable | Evidence location |
|------|-------|-------------|------------------|
| Choose MSIX or WiX/MSI (ADR-005) | DevSecOps Engineer | ADR-005 option selected | `architecture/decisions/ADR-005-*` |
| Build offline wheelhouse from `sbom/requirements.lock` | DevSecOps Engineer | Wheelhouse on isolated build host | `evidence/supply-chain/wheelhouse-manifest.json` |
| Full transitive vulnerability audit | DevSecOps Engineer + security | Disposition for all transitive deps | `sbom/vulnerability-disposition.json` |
| Build and sign Windows package | DevSecOps Engineer | Signed MSIX or MSI with timestamp | `evidence/supply-chain/signed-package-hash.json` |
| Attest FFmpeg, model, and all wheel hashes | DevSecOps Engineer | Hashes on qualified endpoint | `sbom/hash-manifest.json` (endpoint fields filled) |
| Clean-machine install/repair/upgrade/uninstall/rollback | DevSecOps Engineer | All 5 operations documented on managed image | `evidence/supply-chain/install-matrix.json` |

**QG-02 closes when:** Full transitive SBOM clean, signed package attested, 5-operation matrix passes on managed image.

### Track 3 — QG-03: OS Identity, ACL, Encryption, Pen Test (Endpoint Security Lead)

| Step | Owner | Deliverable | Evidence location |
|------|-------|-------------|------------------|
| Provision service identity and data ACL on managed endpoint | Information Security Officer | ACL and identity policy document | `evidence/endpoint/identity-acl-policy.json` |
| Validate STS-123 audit store encryption (DPAPI) on managed endpoint | PQAPS | DPAPI binding to service identity confirmed | `evidence/endpoint/audit-store-encryption.json` |
| Validate STS-103 OS auth and encrypted storage | Information Security Officer + PQAPS | Recovery, revocation, and deletion tests pass on endpoint | `evidence/endpoint/auth-encryption.json` |
| Scoped penetration test | External or internal pen tester | Report: zero unresolved critical or high findings | `evidence/security/pen-test-report.json` |
| Pen test finding remediation | Engineering + PQAPS | All critical/high closed; medium/low accepted with residual-risk decision | Updated report |

**QG-03 closes when:** Service identity and ACL verified, encryption tested, audit store DPAPI confirmed, pen test passes with zero unresolved critical/high findings.

### Track 4 — QG-04: Accessibility and Application Security (Accessibility and Security Lead)

| Step | Owner | Deliverable | Evidence location |
|------|-------|-------------|------------------|
| Re-run automated accessibility and browser regressions | PQAFE | All 4 viewport/theme cases pass; zero console errors | `evidence/quality/browser-uat.json` |
| Manual keyboard-only workflow (full flow: upload → transcribe → review → export → delete) | Accessibility lead | Pass/fail per step; no trap or skip-link failure | `evidence/accessibility/keyboard-manual.json` |
| Supported screen reader workflow (NVDA or JAWS on approved browser) | Accessibility lead | Named dialogs, aria-labels, focus order accepted | `evidence/accessibility/screen-reader-report.json` |
| Penetration test (shared with QG-03 scope) | Pen tester | Application-layer findings resolved | Shared with Track 3 report |

**QG-04 closes when:** Manual keyboard-only passes, screen-reader acceptance recorded, pen test application findings resolved.

### Track 5 — QG-05: Export, Retention, Audit Store Governance (Records and Privacy Lead)

| Step | Owner | Deliverable | Evidence location |
|------|-------|-------------|------------------|
| Records/privacy owner signs `AUDIT_SINGLE_PURPOSE_PRINCIPLE.md` | Data Protection Officer | Signed copy | `evidence/governance/audit-principle-signoff.json` |
| Records/privacy owner approves `STS_AUDIT_MIN_RETENTION_DAYS` floor | Data Protection Officer | Retention policy document | `evidence/governance/retention-policy.json` |
| Approve export destinations and DLP rules | Data Protection Officer | Named approved paths, DLP policy | `evidence/governance/export-dlp-policy.json` |
| Operator training materials reviewed and accepted | Data Protection Officer + PQAFE | Training acknowledgement | `evidence/governance/training-record.json` |
| Deletion and recovery drill executed | Data Protection Officer + operator | Drill evidence: source deleted, audit tree retained, export copies located | `evidence/governance/deletion-drill.json` |

**QG-05 closes when:** Audit principle signed, retention floor approved, export destinations and DLP approved, training and drill evidence accepted.

---

## Phase 2: Environment Qualification

**Duration:** Weeks 10–18 (starts after Phase 1B Track 3 provisions the managed endpoint)
**Gate impact:** Closes QG-06. Can run in parallel with Phase 1B tracks 1/2/4/5.

### QG-06: Performance, Capacity, and Recovery Matrix (Endpoint Platform Lead)

| Measurement | Method | Evidence |
|-------------|--------|---------|
| P50/P95 processing time: clean short audio (≤ 2 min) | Endpoint timing run | `evidence/capacity/perf-short-clean.json` |
| P50/P95 processing time: noisy long audio (≥ 10 min) | Endpoint timing run | `evidence/capacity/perf-long-noisy.json` |
| P50/P95 CPU and memory during transcription | Resource profiler on endpoint | `evidence/capacity/resource-profile.json` |
| Full-disk failure: safe stop, no partial transcript | Forced full-disk condition | `evidence/capacity/full-disk-drill.json` |
| Process termination + restart: job state recovery | Kill signal during transcription | `evidence/capacity/interruption-drill.json` |
| Batch interruption: per-file isolation, no cross-file failure | Mid-batch kill | `evidence/capacity/batch-interruption-drill.json` |
| Upgrade rollback: prior version state accessible | Install upgrade, then rollback | `evidence/capacity/upgrade-rollback.json` |
| Storage capacity threshold: near-limit behavior | Inject near-cap storage | `evidence/capacity/storage-threshold.json` |

**QG-06 closes when:** P50/P95 measures recorded by profile; all recovery drills stop safely; supported hardware matrix frozen.

---

## Pilot Promotion Gate

**Entry condition:** All of the following must be true simultaneously:

| Condition | Verified by |
|-----------|-------------|
| QG-01 passed — sealed eval, human acceptance | AI Quality and Evaluation Engineer + Principal Release Engineer |
| QG-02 passed — signed package, 5-op matrix | DevSecOps Engineer |
| QG-03 passed — identity, ACL, encryption, pen test (zero critical/high) | Information Security Officer + PQAPS |
| QG-04 passed — manual keyboard, screen reader, pen test app layer | Product Security and Accessibility Lead + PQAFE |
| QG-05 passed — audit principle signed, retention, DLP, training, drill | Data Protection Officer + PQAPS |
| QG-06 passed — P50/P95 by profile, all drills safe | IT Systems Engineer + PQAFE |
| QG-08 maintained — validators pass, `promotion_ready=false` is the control | Principal Release Engineer |
| No unresolved critical or high pen test finding | PQAPS |
| `AUDIT_SINGLE_PURPOSE_PRINCIPLE.md` signed by both required parties | Data Protection Officer + principal security/privacy architect |
| `STS_AUDIT_QUERY_ENABLED=false` in production configuration | Engineering + PQAPS |

**Pilot scope:** Controlled, non-production. Synthetic or explicitly authorized low-risk recordings. Single managed endpoint. No regulated workflows, legal-record generation, or multi-user service.

**Not approved at pilot:** Production deployment, general accuracy claims, compliance claims, ROI claims, manifest execution, connector enablement.

---

## Phase 3: Feature Expansion (Post-Pilot)

**Duration:** Weeks 18–30 (starts after pilot gate passes; runs in parallel)
**Dependency:** Pilot gate passed; records/privacy owner approval required before PHI detection starts.

### STS-101 — Speaker Diarization

| Deliverable | Acceptance |
|-------------|-----------|
| Diarization engine integrated locally (pyannote or equivalent) | No cloud call; model hash recorded |
| Per-segment speaker label in transcript and JSON export | E2E test passes |
| Held-out diarization evaluation set (en, 2-speaker minimum) | PQAFE validates subgroup report |
| WER measured with speaker attribution error factored | AI Quality and Evaluation Engineer accepts threshold |
| UI: speaker labels in transcript view with linked playback | Playwright UAT passes |

### STS-119 — PHI/PII/BHI/BII Entity Detection

**Dependencies:** Privacy lead approves NLP approach and threat model before implementation starts.

| Deliverable | Acceptance |
|-------------|-----------|
| Local entity detection (no cloud call; spaCy or equivalent) | Model hash recorded; no network egress |
| Supported categories: PHI, PII, BHI, BII with confidence scores | Documented; false-positive tradeoffs disclosed |
| Flag report co-exported with transcript (not automatic redaction) | Reviewer-triggered |
| Privacy threat model reviewed and accepted | Data Protection Officer sign-off |
| PQAPS validates: no entity text in audit log; detection result not retained beyond export | PQAPS sign-off |

### STS-120 — Redaction Export

**Dependencies:** STS-119 must be done. Records/privacy owner approves scope.

| Deliverable | Acceptance |
|-------------|-----------|
| Reviewer-approved redaction per export run (not automatic) | UI flow enforces per-run gate |
| Original transcript preserved unmodified in local store | Test: source unchanged after redaction export |
| Redacted export clearly labelled and distinguishable from original | UI label + export filename marker |
| Redacted copy deletion tracked in audit/derivation tree | Deletion record in STS-123 tree |

---

## Phase 4: Connector Enablement (Post-Pilot)

**Duration:** Weeks 22–40 (can start planning after pilot gate; implementation blocked on per-connector ADR + threat model)
**Gate impact:** Closes QG-07.
**Hard constraint:** QG-07 is NOT a local-only pilot blocker. Do not let Phase 4 delay or weaken Phase 1B.

### Pre-implementation gate for ALL connectors

No connector story may begin implementation without:
1. Separate ADR approved (beyond ADR-006 architecture)
2. Threat model accepted by Security Architect — Connectors
3. Hostile-input test corpus defined
4. Secret lifecycle (acquisition, rotation, revocation) approved
5. Disabled-by-default configuration committed

### STS-107 — Credential Locker (Windows Credential Manager)

Prerequisite for STS-108, STS-109, STS-121, STS-122.

| Deliverable | Acceptance |
|-------------|-----------|
| Provider contract tests: acquire, redact, expire, revoke | 20-reference cap enforced |
| Redacted audit tests: no secret value in any log, audit, or API response | PQAPS validates |
| Lifecycle tests: revocation, expiry, re-acquisition | Tests pass in isolated environment |

### STS-108 — Password-Protected Archive Extraction

| Deliverable | Acceptance |
|-------------|-----------|
| Security spike: traversal, symlink, bomb, zip-slip corpus | All hostile fixtures rejected |
| Separate archive adapter ADR (approved by Security Architect — Connectors) | ADR merged before code |
| Extraction cleanup and timeout tests | No partial artifact left on failure |
| `STS_PROTECTED_ARCHIVE_ENABLED=false` default confirmed | Feature flag test |

### STS-109 — Zoom OAuth / PKCE

| Deliverable | Acceptance |
|-------------|-----------|
| Zoom Marketplace app approved by IT + Zoom tenant | Approval record |
| OAuth PKCE flow with minimum pinned scopes | Scope-allowlist test |
| Hostile redirect and SSRF tests | All rejected |
| Rate-limit and oversized-response tests | Bounded download enforced |
| `STS_ZOOM_CONNECTOR_ENABLED=false` default confirmed | Feature flag test |

### STS-121 — Teams Connector

| Deliverable | Acceptance |
|-------------|-----------|
| ADR-006 Teams track: Azure AD app registered, minimum delegated scope | IT approval record |
| Token lifecycle: expiry, revocation, re-acquisition | Tests pass |
| Download-then-delete pipeline with audit record | PQAPS validates audit tree entry |
| `STS_TEAMS_CONNECTOR_ENABLED=false` default confirmed | Feature flag test |

### STS-122 — Zoom Connector (STS-107 + STS-109 combined)

Depends on STS-107 (credential locker) and STS-109 (Zoom OAuth) being complete.

**QG-07 closes when:** STS-107 + STS-108 + STS-109 + STS-121 + STS-122 all pass their per-connector acceptance; Security Architect — Connectors approves; all connectors remain disabled by default; zero unresolved critical/high findings.

---

## Summary schedule (weeks from Phase 0 start)

| Phase | Weeks | Key output |
|-------|-------|-----------|
| Phase 0: Governance and staffing | 0–3 | 8 roles named; principle signed; policies defined |
| Phase 1A: Repo work (STS-123, STS-103 interface) | 1–6 | Audit store implemented; STS-103 stub merged |
| Phase 1B Track 1: QG-01 eval | 4–12 | Sealed eval, human acceptance |
| Phase 1B Track 2: QG-02 installer | 4–14 | Signed package, clean-machine matrix |
| Phase 1B Track 3: QG-03 identity/pen test | 4–16 | Endpoint provisioned, pen test clean |
| Phase 1B Track 4: QG-04 accessibility/security | 6–14 | Screen reader pass, pen test app layer |
| Phase 1B Track 5: QG-05 records governance | 4–10 | Retention approved, DLP, training, drill |
| Phase 2: QG-06 performance/recovery | 10–18 | P50/P95 by profile, all drills pass |
| **Pilot gate** | **Week 18+** | **QG-01–06 + QG-08 all passed** |
| Phase 3: STS-101/119/120 | 18–30 | Diarization, PHI detection, redaction |
| Phase 4: STS-107/108/109/121/122 | 22–40 | Connectors enabled under QG-07 |

*All week estimates are notional from Phase 0 start. Actual depends on org capacity, endpoint availability, pen test scheduling, and regulatory review timelines. Phase 1B Track 3 (pen test) is historically the longest single-path constraint.*

---

## Dependency map

```
Phase 0 (staffing + principle)
  └─ unlocks ─ Phase 1B all tracks (need named owners)
  └─ unlocks ─ STS-123 implementation (need principle signed)

Phase 1A (STS-123 impl, STS-103 stub)
  └─ feeds ─ QG-03 (PQAPS validates audit store on endpoint)
  └─ feeds ─ QG-05 (audit store + principle sign-off)

Phase 1B Track 3 (managed endpoint provisioned)
  └─ enables ─ Phase 2 (QG-06 needs qualified endpoint)
  └─ enables ─ STS-103 full delivery

Phase 1B (all tracks) + Phase 2
  └─ required for ─ Pilot Gate

Pilot Gate
  └─ enables ─ Phase 3 (STS-101, STS-119, STS-120)
  └─ enables ─ Phase 4 planning → per-connector ADR → Phase 4 implementation

STS-107 (credential locker)
  └─ prerequisite for ─ STS-108, STS-109, STS-121, STS-122

STS-119 (PHI detection)
  └─ prerequisite for ─ STS-120 (redaction)
```

---

## KPIs and success criteria

| KPI | Target | Measured by |
|-----|--------|-------------|
| Pilot gate week | Week 18 from Phase 0 start | Principal Release Engineer |
| Pen test critical/high findings at gate | 0 unresolved | PQAPS |
| QG-01 WER by subgroup | Within AI Quality and Evaluation Engineer–accepted threshold | PQAFE + AI Quality and Evaluation Engineer |
| QG-06 P95 processing time (clean short audio) | ≤ 2× realtime | IT Systems Engineer |
| Test suite | 465+ passing; 0 failed | CI on every merge |
| Branch coverage | ≥ 86% | CI on every merge |
| Architecture gate compliance | 23/23 passing | `validate_architecture.py` |
| Audit store HMAC failures | 0 (append-only enforced) | PQAPS on managed endpoint |
| Export API audit-byte leakage | 0 bytes in any export response | Negative-control test |

---

## Decisions required before work can start

| Decision | Who decides | Unblocks |
|----------|-------------|---------|
| Name all 8 role holders | Product Owner | Every phase |
| Confirm DPAPI vs IT-managed key for audit store | Data Protection Officer + Information Security Officer | STS-123 implementation |
| Choose MSIX vs WiX/MSI for installer (ADR-005) | DevSecOps Engineer | QG-02 Track 2 |
| Define managed endpoint hardware matrix | IT Systems Engineer | QG-06 Track, Phase 2 |
| Approve domain eval dataset and threshold protocol | AI Quality and Evaluation Engineer | QG-01 Track 1 |
| Approve PHI/PII NLP approach | Data Protection Officer | STS-119 implementation |
| Approve per-connector ADRs and threat models | Security Architect — Connectors | Phase 4 implementation |

---

*This roadmap is reviewed at every gate closure and updated whenever a story status changes or a new risk is registered. The authoritative promotion state is always `evals/quality-roadmap.json`.*
