# Operator Deployment Checklist — Verbatim STS

Version: 1.0 | Generated: 2026-07-30 | Author: Virtual AI — Information Security Officer

**STATUS: DRAFT — DPO review and approval required before use in a real deployment.**

---

## Pre-deployment

### Storage and directory configuration

- [ ] IT has reviewed and approved `STS_DATA_DIR` storage path and permissions
- [ ] `STS_AUDIT_DIR` is set to a directory outside `STS_DATA_DIR` (production requirement per ADR-007)
- [ ] `STS_AUDIT_DIR` has owner-only permissions (700 on Linux/macOS; restricted ACL on Windows)
- [ ] `STS_AUDIT_MIN_RETENTION_DAYS` set to 365 or organizational policy floor (whichever is greater)
- [ ] `STS_AUDIT_MAX_RETENTION_DAYS` confirmed with records owner (default 2555 / 7 years)

### Feature flags — all must be confirmed disabled

- [ ] `STS_AUDIT_QUERY_ENABLED=false` confirmed (default; do not enable without DPO authorization and named audit request)
- [ ] `STS_ZOOM_CONNECTOR_ENABLED=false` (default; feature not yet approved — requires STS-122 and ADR-006)
- [ ] `STS_MANIFEST_INTAKE_ENABLED=false` (default)
- [ ] `STS_PROTECTED_ARCHIVE_ENABLED=false` (default)
- [ ] `STS_TEAMS_CONNECTOR_ENABLED=false` (default; requires STS-121 and ADR-006)

### Supply chain verification

- [ ] Whisper model file hash verified against `sbom/hash-manifest.json`
- [ ] FFmpeg binary hash verified against `sbom/hash-manifest.json`
- [ ] Transitive dependency lock (`sbom/requirements.lock`) reviewed by IT
- [ ] Vulnerability disposition (`sbom/vulnerability-disposition.json`) reviewed — no unresolved critical or high findings

### Package and signing (BLOCKING — human required)

- [ ] Installer signed with EV certificate (PENDING — QG-02 gate; IT packaging lead required)
- [ ] Signed package verified on clean managed endpoint (PENDING — QG-02 gate)

### Governance sign-offs required before pilot

- [ ] DLP matrix (`evidence/governance/dlp-matrix.json`) approved by DPO
- [ ] Retention policy (`evidence/governance/retention-policy.json`) approved by DPO
- [ ] Audit Single-Purpose Principle sign-off (`evidence/governance/audit-principle-signoff.json`) on file
- [ ] Operator training materials delivered and knowledge-check sign-off obtained for all operators

---

## Post-installation

### Automated checks

- [ ] Run `python scripts/validate_architecture.py` — no FAIL items
- [ ] Run `python scripts/validate_quality_gates.py --write-report` — output matches expected gate state
- [ ] Run `python -m pytest --tb=short -q` — all tests pass

### Application health verification

- [ ] Application starts and health endpoint responds with `200 OK`
- [ ] `STS_DATA_DIR` created with correct permissions
- [ ] `STS_AUDIT_DIR` created and confirmed separate from `STS_DATA_DIR`
- [ ] No unexpected network connections observed during startup (local-only per ADR-001)

### Deletion drill (required before first production use)

- [ ] Complete deletion drill per `evidence/governance/deletion-drill-guide.md`
- [ ] All six pass/fail checks recorded and passed
- [ ] Drill results filed with records owner
- [ ] Note: deletion drill requires STS-123 (AuditStore) to be implemented — BLOCKED on STS-123

---

## Recurring (quarterly)

- [ ] Review audit tree directory — confirm files not manually deleted
- [ ] Confirm retention floor not violated for any job (oldest job age < STS_AUDIT_MIN_RETENTION_DAYS or deletion was legitimate)
- [ ] Review DPO approval records — confirm still current and DPO signatory still holds the role
- [ ] Re-run deletion drill per `evidence/governance/deletion-drill-guide.md` and file dated results
- [ ] Review event log directory — confirm no unexpected growth or gaps

---

## Pilot promotion gates — all must pass before production use

| Gate | Description | Owner role | Current state |
|------|-------------|------------|---------------|
| QG-01 | Representative transcription quality — 46+ cases, domain SME acceptance | Domain evaluation lead | blocked |
| QG-02 | Signed installer, upgrade, uninstall, rollback qualification on managed endpoint | IT packaging and security lead | partial |
| QG-03 | OS identity, ACL, DPAPI encryption, backup, recovery, penetration acceptance | Endpoint security lead | blocked |
| QG-04 | Accessibility and application-security acceptance on approved browser matrix | Accessibility and application security lead | partial |
| QG-05 | DLP matrix and retention policy approved by DPO; deletion drill passed; training deployed | Records and privacy lead | partial |
| QG-06 | Performance and recovery matrix on managed endpoint | Endpoint platform lead | partial |
| QG-08 | Truthful evidence and fail-closed promotion control | Release governance lead | passed |

QG-07 (credential, protected archive, Zoom connector) is not blocking for the local-only pilot.

**No gate may be waived. All six promotion-blocking gates must be in `passed` state with
reproducible evidence before pilot approval. Missing or stale evidence blocks promotion.**
