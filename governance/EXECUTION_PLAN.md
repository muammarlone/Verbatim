# Verbatim STS — Prioritized Execution Plan

*Version 1.0 — 2026-07-31. Owner: Principal Architect + Product Owner.*
*Authority: `governance/QUALITY_ROADMAP.md`, `evals/quality-roadmap.json`, `governance/BACKLOG.md`.*

---

## Decision

**Goal:** Close all six pilot-blocking gates (QG-01 through QG-06). Reach `promotion_ready=true`.
**Current state:** 475 tests pass. STS-123 implemented and merged. QG-08 passed. Five gates partial, one blocked.
**Constraint:** Virtual AI engineers can implement all repo work. They cannot sign packages, provision managed endpoints, conduct independent pen tests, or manually operate screen readers. Those are explicit human blockers.

---

## Gate inventory and current gap

| Gate | Status | AI-closable gap | Human-required gap |
|------|--------|----------------|-------------------|
| QG-01 | PARTIAL | Harness complete, 46 fixtures catalogued | Real recording dataset; domain SME threshold acceptance |
| QG-02 | PARTIAL | Offline wheelhouse script, MSIX build config (STS-110) | EV signing cert; clean-machine install on managed endpoint |
| QG-03 | BLOCKED | Auth contract, threat model draft, Credential Locker stub (STS-103) | Managed endpoint; service identity; DPAPI real test; pen test |
| QG-04 | PARTIAL | OWASP automation hardening, CSP tightening | Independent pen test (zero unresolved critical/high); manual screen reader |
| QG-05 | PARTIAL | All evidence drafted and committed | DPO approval (muammarlone@gmail.com) of dlp-matrix.json + retention-policy.json |
| QG-06 | PARTIAL | Synthetic Docker profiling scripts | Real P50/P95 on managed corporate Windows endpoint |
| QG-07 | BLOCKED | Not pilot-blocking | Connector ADRs + threat models (Phase 4) |
| QG-08 | PASSED | — | — |

---

## Prioritized execution tiers

### Tier 1 — AI implements now (repo work, no endpoint required)

These items produce concrete code, tests, and evidence immediately. They advance gates directly
or complete the prerequisite work before human gates can open.

#### T1-A: STS-103 — OS Auth Interface Stub (advances QG-03)

**Story:** OS-backed user authentication and encrypted application storage.
**Why now:** QG-03 is fully blocked. The repo work (auth contract, threat model draft, stub) is
the prerequisite before any human gate work can begin. Managed-endpoint verification follows.

**Tasks:**
1. Draft `architecture/decisions/ADR-008-os-auth.md` — Windows Credential Locker design,
   identity model, scope limitations, threat vectors, rejected alternatives.
2. Create `src/secure_transcribe/auth.py` — `AuthProvider` interface with:
   - `is_authenticated() -> bool` — always `True` in dev (no-op stub)
   - `get_credential(key: str) -> str | None` — returns None in dev
   - Windows Credential Locker implementation behind `STS_OS_AUTH_ENABLED=false` flag
   - No plaintext credential storage anywhere in the code path
3. Draft threat model: `architecture/threat-model/STS-103-threat-model.md`
   - Assets: user identity, session token, stored credentials
   - Threats: token theft, credential exfiltration, bypass, privilege escalation
   - Controls: Windows session binding, DPAPI encryption, no-export guard
4. Write `tests/test_auth.py` — stub behavior (disabled by default), no-plaintext enforcement,
   interface contract tests (12+ tests).
5. Update `BACKLOG.md` STS-103 → `done` after acceptance criteria met.

**Acceptance criteria:** ADR-008 accepted; stub merged; `STS_OS_AUTH_ENABLED` defaults false;
no credential in plaintext anywhere; threat model reviewed by PQAPS; tests pass.
**Owner:** Virtual AI — Information Security Officer (AI)
**Dependency:** None — can start immediately.
**Gate impact:** QG-03 baseline established. Endpoint verification and pen test remain as human gates.

---

#### T1-B: STS-110 — Installer Build Automation (advances QG-02)

**Story:** IT can deploy, repair, upgrade, and uninstall a signed Windows package.
**Why now:** ADR-005 (MSIX vs WiX/MSI) is already done. The build scripts and offline wheelhouse
automation can be completed without a signing certificate. Signing is the human gate.

**Tasks:**
1. Create `scripts/build/build_offline_wheelhouse.ps1` — downloads all pinned packages from
   `sbom/requirements.lock` into `dist/wheelhouse/` for air-gapped install. Validates against
   lock file hashes. Production guard: `VERBATIM_BUILD_PRODUCTION_WHEELHOUSE` must be set.
2. Create `scripts/build/build_msix.ps1` — MSIX manifest template, directory layout, packaging
   steps. Does NOT self-sign. Contains `VERBATIM_INSTALLER_PRODUCTION_READY` guard — installer
   must fail if guard is not set to `signed-and-qualified` by IT.
3. Create `scripts/build/verify_wheelhouse_hashes.ps1` — verifies every wheel hash against
   `sbom/requirements.lock` before install. Fails fast if any hash mismatches.
4. Write `tests/test_installer_scripts.py` — guard enforcement tests (installer must fail without
   guard), hash verification tests, manifest structure validation (12+ tests).
5. Update `sbom/hash-manifest.json` notes to indicate wheelhouse script is ready; hashes
   remain null until IT verifies on managed endpoint.

**Acceptance criteria:** Build scripts present; production guards enforce; hash verification
passes; tests pass; signing explicitly blocked pending IT.
**Owner:** Virtual AI — DevSecOps Engineer (AI)
**Dependency:** ADR-005 (done). No signing cert needed for repo work.
**Gate impact:** QG-02 partial advance. Signing and clean-machine install remain as human gates.

---

#### T1-C: QG-04 Application Security Hardening (closes partial gap)

**Story:** Tighten remaining OWASP controls before pen test.
**Why now:** Pen test is a hard human gate. Presenting the tightest possible code posture before
the pen test reduces finding count and increases the chance QG-04 closes on first pass.

**Tasks:**
1. Read current `src/secure_transcribe/app.py` security headers. Verify and tighten:
   - `Content-Security-Policy`: eliminate any wildcard sources; add `script-src 'self'` only.
   - `X-Content-Type-Options: nosniff` — confirm present.
   - `X-Frame-Options: DENY` — confirm present.
   - `Referrer-Policy: no-referrer` — confirm present.
   - `Permissions-Policy` — restrict camera/microphone/geolocation.
2. Audit all file upload paths for path traversal: confirm no user-controlled path component
   reaches `os.path.join` or `Path()` without sanitization.
3. Audit all export endpoints: confirm no SSRF vector (no user-controlled URL fetch).
4. Run existing OWASP test suite (`tests/test_owasp*.py`) and confirm all pass.
5. Add negative-control tests for any new headers (15+ total security header tests).
6. Write `evidence/security/pre-pentest-hardening-report.md` documenting each control checked.

**Acceptance criteria:** All automated security tests pass; hardening report committed;
no wildcard CSP sources; no path traversal; no SSRF; PQAPS reviews.
**Owner:** Virtual AI — Product Security and Accessibility Lead (AI)
**Dependency:** None. Can run in parallel with T1-A and T1-B.
**Gate impact:** QG-04 partial advance. Pen test and screen reader remain as human gates.

---

#### T1-D: QG-06 Synthetic Performance Profiling (closes partial gap)

**Story:** Measure P50/P95 on synthetic workloads in Docker.
**Why now:** The measurement protocol is in place. Docker profiling can be automated now.
Real managed-endpoint profiling requires human IT access — that's the remaining gate.

**Tasks:**
1. Create `scripts/perf/run_synthetic_profiling.ps1` (or `.py`) — runs Docker-based load
   simulation with known synthetic fixtures, captures:
   - P50/P95 wall-clock processing time per file size bracket (small/medium/large)
   - Peak CPU %, peak RSS memory MB
   - Temp storage high-water mark
   - Timeout/failure rate
   Writes results to `evidence/capacity/docker-profiling-{date}.json`.
2. Define `evidence/capacity/profiling-protocol.json` — test cases, fixture sizes, thresholds
   (baseline values from Docker simulation, clearly labeled as non-endpoint).
3. Run the profiling script in Docker and commit results with explicit caveat:
   `"environment": "docker_dev_machine"`, `"not_qualified_endpoint": true`.
4. Write `tests/test_perf_script.py` — script runs without crash, output schema valid (8+ tests).

**Acceptance criteria:** Profiling script runs; results committed with dev-machine caveat;
schema valid; managed-endpoint run explicitly blocked pending IT access.
**Owner:** Virtual AI — IT Systems Engineer (AI)
**Dependency:** Docker installed (STS-111 done). No managed endpoint needed.
**Gate impact:** QG-06 partial advance. Corporate endpoint profiling remains as human gate.

---

### Tier 2 — Human actions required (blocked until organizational capacity)

These cannot be completed by AI. They are documented here so the Product Owner knows exactly
what to request and from whom.

#### T2-A: QG-05 — DPO Approval (Product Owner action)

**Owner:** muammarlone@gmail.com (Data Protection Officer, course context)
**Action required:** Review and approve:
- `evidence/governance/dlp-matrix.json` — 5 data types with sensitivity classification
- `evidence/governance/retention-policy.json` — per-type retention rules
**Current state:** Both files drafted and committed 2026-07-30.
**What to check:** DT-03 audit tree export prohibition; 365-day retention floor; event log gap acknowledged.
**Approval mechanism:** Update `evidence/governance/dlp-matrix.json` field `"approved_by"` and
`evidence/governance/retention-policy.json` field `"approved_by"` with your name/email and date.
Commit the updated files. This closes QG-05.
**Unblocks:** QG-05 final close.

---

#### T2-B: QG-01 — Domain SME Threshold Acceptance

**Owner:** Domain Subject Matter Expert (legal, medical, or finance vertical)
**Action required:**
1. Review `evidence/eval/threshold-protocol.json` — proposed WER thresholds 0.15/0.20/0.25.
2. Define consequential error categories for target verticals (e.g., medication name errors in
   medical; party name errors in legal).
3. Curate or approve a sealed real-recording evaluation dataset (minimum 20 real cases covering
   target domains). Sign off on dataset card.
4. Run eval harness against real dataset on qualified endpoint with Whisper model loaded.
5. Accept or reject WER thresholds based on actual results.
**Current state:** 46 synthetic fixtures in place; harness ready; thresholds are draft INFERENCE.
**Unblocks:** QG-01 close.

---

#### T2-C: QG-02 — Signed Installer and Clean-Machine Qualification

**Owner:** Virtual AI — DevSecOps Engineer (AI) prepares; human IT engineer with EV cert executes.
**Action required (human):**
1. Obtain EV code-signing certificate from approved CA.
2. Run `scripts/build/build_offline_wheelhouse.ps1` on clean managed machine.
3. Run `scripts/build/build_msix.ps1`, sign package with EV cert.
4. Execute install, repair, upgrade, uninstall, rollback on isolated test machine.
5. Record evidence: `evidence/installer/clean-machine-matrix.json`.
**Current state:** AI produces build scripts (T1-B above). Signing requires human.
**Unblocks:** QG-02 close.

---

#### T2-D: QG-03 — Managed Endpoint Identity, Encryption, Pen Test

**Owner:** Named Information Security Officer (human, organizational authority)
**Action required (human):**
1. Configure service identity (Windows service account with minimum privilege) on managed endpoint.
2. Set `STS_DATA_DIR` to IT-controlled path with 700 ACL; verify DPAPI binds to service identity.
3. Configure `STS_AUDIT_TREE_DIR` separately from `STS_DATA_DIR` (owner-only permissions).
4. Verify backup exclusion (audit dir not backed up to cloud without DPO approval).
5. Verify indexing exclusion (Windows Search / Spotlight not indexing data dir).
6. Commission independent pen test. Resolve all critical and high findings.
7. Record `evidence/security/pentest-report-summary.json` and `evidence/os/endpoint-config.json`.
**Current state:** STS-103 auth stub (T1-A) prepares the code baseline. Endpoint work requires human.
**Unblocks:** QG-03 close.

---

#### T2-E: QG-04 — Manual Screen Reader and Independent Pen Test

**Owner:** Named Product Security and Accessibility Lead (human for manual UAT)
**Action required (human):**
1. Run full keyboard-only workflow on approved browser matrix (Chrome, Edge).
2. Run NVDA or JAWS screen reader through upload, review, export, delete workflow.
3. Record pass/fail per workflow step in `evidence/accessibility/screen-reader-matrix.json`.
4. Independent pen test result from QG-03 covers QG-04 app security gate.
**Current state:** Automated accessibility suite done (4 Chromium cases). Manual step is human gate.
**Unblocks:** QG-04 close.

---

#### T2-F: QG-06 — Managed Endpoint Performance Matrix

**Owner:** Virtual AI — IT Systems Engineer (AI) prepares scripts; human IT runs on endpoint.
**Action required (human):**
1. Run `scripts/perf/run_synthetic_profiling.ps1` on qualified corporate Windows endpoint.
2. Capture P50/P95, CPU, memory, temp storage for short/long/clean/noisy/interrupted cases.
3. Run full-disk, process termination, restart, partial batch, model unavailable drills.
4. Record `evidence/capacity/managed-endpoint-profiling.json`.
**Current state:** Docker profiling complete (T1-D above). Corporate endpoint run requires human IT.
**Unblocks:** QG-06 close.

---

### Tier 3 — Post-pilot (not pilot-blocking)

These are planned after the pilot gate passes. Do not implement before pilot unless explicitly
authorized by the Product Owner.

| Story | Phase | Dependency |
|-------|-------|-----------|
| STS-101 Diarization | Phase 3 | Pilot passed; diarization eval lead named |
| STS-119 PHI/PII detection | Phase 3 | Privacy lead approval; threat model accepted |
| STS-120 Redaction | Phase 3 | STS-119 done; DPO approval |
| STS-107 Windows Credential Locker | Phase 4 | STS-103 done; credential threat model accepted |
| STS-108 Protected archive extraction | Phase 4 | Security spike, traversal corpus, approved ADR |
| STS-109 Zoom OAuth/PKCE | Phase 4 | ADR-006; Zoom Marketplace approval; STS-107 done |
| STS-110 Teams connector | Phase 4 | ADR-006; Azure AD registration; STS-107 done |
| STS-121 Zoom Cloud connector | Phase 4 | STS-109 done; Zoom IT approval |
| STS-122 Teams recording connector | Phase 4 | STS-121 done; Teams IT approval |

---

## Execution sequence

```
NOW (AI, parallel)
  T1-A  STS-103 OS auth stub          → baseline for QG-03
  T1-B  STS-110 installer scripts     → baseline for QG-02
  T1-C  QG-04 security hardening      → pre-pentest posture
  T1-D  QG-06 Docker profiling        → baseline for QG-06

HUMAN ACTIONS (Product Owner / organizational)
  T2-A  QG-05 DPO approval            → closes QG-05 (quickest close)
  T2-B  QG-01 domain SME acceptance   → closes QG-01
  T2-C  QG-02 signing + install       → closes QG-02
  T2-D  QG-03 managed endpoint        → closes QG-03 (longest lead time)
  T2-E  QG-04 screen reader + pentest → closes QG-04
  T2-F  QG-06 endpoint profiling      → closes QG-06

PILOT GATE (all 6 gates closed + QG-08 already passed)
  → promotion_ready=true
  → Principal Release Engineer records promotion decision

POST-PILOT
  T3    Diarization, PHI detection, connectors
```

---

## Decision gates

| Decision | Owner | Trigger |
|----------|-------|---------|
| Approve DT-03 export prohibition and 365-day floor | DPO (muammarlone@gmail.com) | Before QG-05 closes |
| Accept WER thresholds for target verticals | Domain SME | Before QG-01 closes |
| Authorize managed-endpoint DPAPI test | IT + Information Security Officer | Before QG-03 opens |
| Commission and scope pen test | Information Security Officer | Before QG-03/QG-04 close |
| Approve MSIX signing and release | DevSecOps + IT | Before QG-02 closes |
| Authorize post-pilot connector work | Product Owner | After pilot gate passed |
| Authorize PHI/PII detection (STS-119) | DPO + privacy lead | After pilot; before Phase 3 starts |

---

## KPIs

| KPI | Current | Target |
|-----|---------|--------|
| Passing tests | 475 | 500+ (after T1-A, T1-B, T1-C, T1-D) |
| Branch coverage | 86% | ≥ 88% (service.py and auth.py) |
| Pilot-blocking gates passed | 1 of 7 (QG-08) | 7 of 7 |
| Human-blocked gates remaining | 6 | 0 |
| WER on real eval set | not measured | < 0.15 pass threshold |
| Audit store HMAC tests | 10 | 10 (stable) |
| Security header controls | partial | full (post T1-C) |

---

## What invalidates this plan

- Product Owner reassigns piloting to a different endpoint type (non-Windows) — re-scope QG-03/QG-06.
- Domain SME rejects 0.15 WER threshold — renegotiate; may require model upgrade.
- Pen test finds unresolved critical finding — block until resolved; plan additional hardening sprint.
- Legal/compliance requirement changes DT-03 retention from 365 to longer — update `STS_AUDIT_MIN_RETENTION_DAYS`, re-sign.
- Phase 4 connector work authorized before pilot — enforce hard stop; Phase 4 must not weaken Phase 1 baseline.

---

*This plan is the authoritative execution reference. Update it when gate states change.*
*Governance files take precedence: `QUALITY_ROADMAP.md` > this plan > individual story acceptance criteria.*
