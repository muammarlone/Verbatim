# Principal QA Analyst Charters

*Version 1.0 — 2026-07-30. Governed by the principal architect quality roadmap.*

---

## Purpose

Two Principal QA Analyst roles are established to provide independent, structured quality
assurance coverage across the two orthogonal risk axes that block corporate pilot:

1. **Privacy and security** — that the product handles audio, transcripts, credentials, and
   derived artifacts within controlled, auditable, policy-compliant boundaries at all times.
2. **Functionality and end-to-end validation** — that every stated functional requirement and
   non-functional requirement (NFR) is exercised, measured, and traceable to passing evidence
   before promotion is claimed.

Neither role may approve promotion. Both roles feed evidence into the promotion-blocking gates
owned by named technical leads. Their output is evidence and findings, not a green-light.

---

## Role 1: Principal QA Analyst — Privacy and Security (PQAPS)

### Charter

Validate all security controls, privacy boundaries, threat model coverage, and audit-trail
integrity for the Verbatim pilot boundary. Coordinate penetration testing scope. Certify that
no unresolved critical or high finding exists within the pilot boundary before QG-03 or QG-04
(security portion) can be declared `passed`.

### Scope

| Gate | Responsibility |
|------|---------------|
| QG-03 | OS identity, storage ACL, encryption, backup exclusion, deletion propagation, recovery |
| QG-04 (security) | OWASP automated suite, manual application security acceptance, header/egress regressions |
| QG-07 | Connector threat model validation — credential, archive, Zoom (not-started gates) |
| STS-103 | OS-backed auth and encrypted storage — threat model and pen test readiness |
| STS-107/108/109 | Blocked stories — ensure ADR and threat model preconditions are met before dev |

### Ongoing responsibilities

- **Threat model validation**: Review and sign off all threat model documents before associated
  code is merged. Verify STRIDE coverage for each trust boundary in `architecture/`.
- **Content-free audit event verification**: Confirm that every audit log event emitted by the
  application contains no transcript text, no file paths, no model output, and no PII/PHI
  spans. Run `tests/test_audit_events.py` (or equivalent) as the canonical check.
- **Encrypted audit store validation (ADR-007)**: When STS-123 is implemented, validate that
  (a) the audit store is encrypted with DPAPI or IT-managed key, (b) every record carries a
  valid HMAC-SHA-256 tag, (c) the file is append-only (no record mutates after write), (d) the
  retention floor `STS_AUDIT_MIN_RETENTION_DAYS` is enforced and cannot be overridden by the
  application, and (e) the audit query endpoint `STS_AUDIT_QUERY_ENABLED` defaults to false.
- **Purpose limitation verification**: Confirm that no audit tree content is reachable via
  `/api/jobs/{id}/export`, batch export, or any normal UI path. Run a negative-control test
  that calls all export endpoints and asserts zero audit-record bytes in the response.
- **Proprietary boundary check**: Confirm that the operator manual and records-owner sign-off
  stub explicitly state that derivation tree records are proprietary internal records, not
  deliverables, and must not be used for analytics, benchmarking, or AI model training.
- **Export boundary audit**: Validate that every export operation appends an export record to
  the derivation tree and that deletion of the managed copy does not purge the audit record.
- **Feature flag enforcement**: Verify that `STS_MANIFEST_INTAKE_ENABLED`,
  `STS_PROTECTED_ARCHIVE_ENABLED`, and `STS_ZOOM_CONNECTOR_ENABLED` default to `false` and
  that tests confirm no credential-adjacent code path is reachable from a default installation.
- **Pen test coordination**: Define scope, supply architecture diagrams and threat model to
  the testing team, triage findings by severity (critical/high block promotion), and track
  remediation to closure for QG-03.

### Gap analysis — current state (2026-07-30)

| Area | Status | Gap |
|------|--------|-----|
| OWASP automated suite (QG-04) | partial — automated tests pass | Manual pen test not scheduled |
| OS identity and storage ACL (QG-03) | blocked — not started | Service identity, ACL, encryption not verified on managed endpoint |
| Audit log content-free check | tests exist | No test verifies log retention after job deletion |
| Encrypted audit store (ADR-007/STS-123) | not started | No derivation tree, no encrypted audit store, no HMAC integrity, no purpose-limitation enforcement |
| Export audit record | not started | No audit record on export; no retention proof after deletion |
| Audit store encryption at rest | not started | QG-03 open; DPAPI/IT-key encryption not implemented or verified on managed endpoint |
| Purpose-limitation no-export guard | not started | Export API not tested for absence of audit-record bytes; negative control test missing |
| Threat models for STS-107/108/109 | not started | Blocking dev — no ADR, no threat model, no hostile-input protocol |

### Regression protocol

Run before any pull request touching `app/`, `api/`, `middleware/`, `auth/`, or any
`STS_*` feature flag:

```powershell
python -m pytest tests/test_security.py tests/test_audit.py tests/test_supply_chain.py -v
python -m pytest tests/ -k "owasp or security or privacy or audit" -v
```

Re-run the full suite (`python -m pytest`) after any dependency change.

---

## Role 2: Principal QA Analyst — Functionality and End-to-End Validation (PQAFE)

### Charter

Validate that every functional requirement (FR) in the backlog and every non-functional
requirement (NFR) stated in architecture and governance documents is exercised by a traceable,
passing test or recorded evidence artifact before promotion. Own the requirements traceability
matrix (RTM). Certify that no FR or NFR remains without evidence mapping when QG-01, QG-04
(accessibility portion), QG-05, or QG-06 are declared ready for owner review.

### Scope

| Gate | Responsibility |
|------|---------------|
| QG-01 | Domain evaluation evidence — language, noise, speaker, domain subgroups |
| QG-04 (accessibility) | Keyboard-only and screen-reader workflows, contrast, skip-link, named dialogs |
| QG-05 | Export destination, retention/DLP rules, deletion-drill evidence, training records |
| QG-06 | Endpoint performance matrix — P50/P95 time, CPU, memory, storage, interruption |

### Ongoing responsibilities

- **Requirements traceability matrix (RTM)**: Maintain a mapping of every story ID (STS-001
  through STS-122+) to the test IDs and evidence artifacts that satisfy its acceptance criteria.
  A story with `done` status that has no traceable passing test is a gap.
- **NFR coverage mapping**: Map each NFR class to evidence. See the NFR inventory below.
- **E2E regression**: Own the Playwright-based end-to-end suite. Run the full suite before
  any merge to `main` and after any UI or API change. Zero regressions = required.
- **Eval harness oversight**: Validate that `tests/eval/` fixtures remain sealed, that WER
  thresholds are reviewed after any model change, and that the 46-case synthetic eval set
  reflects current supported languages and domains.
- **Batch workflow regression**: Validate the two-file batch smoke (`evidence/batch/`) after
  any change to `batch.py`, `service.py`, or any export format handler.
- **NFR gap escalation**: When a measured NFR (e.g. P95 processing time, storage cap) falls
  outside its threshold, escalate to the gate owner before merging the triggering change.

### NFR inventory and coverage status

| NFR class | Threshold | Evidence artifact | Coverage status |
|-----------|-----------|-------------------|-----------------|
| Processing latency | ≤ 2× realtime for clean short audio | Synthetic smoke (16.18 s / 9.19 s) | measured — synthetic only |
| Storage cap | ≤ configured `STS_MAX_UPLOAD_BYTES` | Upload cap tests | automated |
| Duration cap | ≤ configured `STS_MAX_DURATION_SECONDS` | Duration budget tests | automated |
| Concurrent job limit | 1 active job | `test_processor_submit_*` | automated |
| Transcription timeout | Killable worker within `STS_TRANSCRIPTION_TIMEOUT` | `test_processor_*` timeout | automated |
| Non-recursive batch scan | Subdirectory files excluded | `test_batch_*` | automated |
| Output non-overwrite | Existing outputs not clobbered | `collision_rejection` tests | automated |
| Keyboard navigation | Full workflow without mouse | Playwright keyboard tests (QG-04 partial) | partial |
| Screen reader | Named dialogs, skip-link, aria-labels | Manual — not run | blocked |
| Contrast ratio | WCAG 2.1 AA | Playwright contrast check | partial — automated only |
| Horizontal overflow | Zero at 375/768/1440 px | Playwright viewport tests | automated |
| Console error budget | Zero errors on golden path | Playwright UAT, recorded demos | passing |
| Egress budget | Zero unexpected network requests | Playwright network intercept | automated |
| Endpoint CPU cap | P95 ≤ TBD — endpoint not yet profiled | QG-06 protocol defined | not started |
| Endpoint memory cap | P95 ≤ TBD — endpoint not yet profiled | QG-06 protocol defined | not started |
| Full-disk recovery | App fails gracefully, no partial writes | QG-06 drill — not run | not started |
| Deletion completeness | Source + derived artifacts removed | Deletion propagation tests | automated |
| Retention sweep | Files beyond threshold swept | Retention sweep tests | automated |

### Gap analysis — current state (2026-07-30)

| Area | Status | Gap |
|------|--------|-----|
| RTM — STS-001 through STS-118 | done or evidence exists | No RTM document — mapping is implicit in backlog |
| RTM — STS-119 through STS-122 | not_started | Stub tests exist; no acceptance evidence |
| NFR — keyboard-only E2E | partial | Automated tab-nav only; no human-performed keyboard-only workflow recorded |
| NFR — screen reader | blocked | No manual run; no assistive-technology environment set up |
| NFR — endpoint performance | not started | No baseline measurement on managed endpoint (QG-06) |
| NFR — full-disk and interruption recovery | not started | Drills defined in QG-06 protocol; not executed |
| QG-01 eval set | not started | STS-104 synthetic fixtures built; sealed real-domain set not defined |
| QG-05 export/retention drills | not started | DLP matrix defined; no operator training record or deletion-drill evidence |
| Transcript provenance tree | not started | No chain-of-custody record; downstream audit cannot verify derivation (STS-123) |

### Regression protocol

Run before any pull request touching `app/`, `api/`, `batch.py`, `service.py`, `ui/`,
or any export handler:

```powershell
python -m pytest -v
python -m pytest tests/eval/ -v
```

Run Playwright suite for any UI change:

```powershell
python tests/browser/run_uat.py
```

Re-run the recorded single-file and batch smoke workflows (synthetic fixtures only) after any
change to the transcription pipeline or export formats. Record new evidence if a measurable
result changes.

---

## Architecture gap: Transcript Derivation Tree (STS-123)

*Identified by principal audit and security architect review, 2026-07-30.*

### Decision required

Verbatim does not currently maintain a structured, immutable provenance record linking each
audio source artifact to its extraction parameters, transcription model version and hash,
segment outputs, revision history, export artifacts, and deletion records. In regulated
enterprise use, this chain of custody is required for legal admissibility and records audits.

### Current state

- FACT: Job model records status, created/updated timestamps, source path, and transcript path.
- FACT: STS-102 added revision history as mutable corrections stored alongside the transcript.
- FACT: Audit log events are content-free but are not structured as a per-job derivation tree.
- FACT: Deletion removes the managed source and derived files with no retained proof of prior state.
- ASSUMPTION: The current approach is acceptable for the synthetic demonstration phase.
- HYPOTHESIS: A regulated corporate pilot will require a provenance tree for records defensibility.

### Target architecture (STS-123)

A **Transcript Derivation Tree** per job, stored as an append-only NDJSON file alongside
each job, structured as follows:

```
SourceRecord      { job_id, source_hash (SHA-256), size_bytes, format, duration_seconds, ingested_at }
ExtractionRecord  { ffmpeg_version, params_hash, output_hash, extracted_at }
TranscriptionRecord { model_id, model_hash, language, params_hash, segment_count, transcribed_at }
Segment[]         { index, start_ms, end_ms, text_hash, avg_logprob, no_speech_prob }
Revision[]        { revision_id, segment_index, operation, original_hash, corrected_hash, revised_at }
ExportRecord[]    { format, destination_scope, content_hash, exported_at }
DeletionRecord    { scope, deleted_at, surviving_artifacts[] }
```

Key properties:
- **Append-only**: no record is modified after written; corrections add revision nodes.
- **Content-free text fields**: text stored as SHA-256 hash only; the actual transcript stays in
  the existing transcript file.
- **Retained after deletion**: the derivation tree file survives job deletion under a configurable
  retention period, supporting post-deletion audit queries.
- **Cryptographically anchored**: each step hashes its inputs and the prior step's output hash,
  creating a tamper-evident chain.

### Roadmap entry

See STS-123 in the backlog (added 2026-07-30). Gate dependency: QG-05 (records and privacy
owner must approve tree retention scope and deletion-proof requirements before implementation).

### NFR implications

- Storage overhead: one NDJSON file per job, estimated < 4 KB for a typical single-speaker session.
- No transcript text in the tree file: privacy boundary maintained.
- Retention period: configurable via `STS_AUDIT_TREE_RETENTION_DAYS`; default TBD by records owner.
- The PQAPS role must validate append-only enforcement and hash integrity before QG-05 closes.
- The PQAFE role must add derivation-tree acceptance tests to the RTM for STS-123.

---

## Audit Single-Purpose Principle — non-waivable gate

The **Audit Single-Purpose Principle** (`governance/AUDIT_SINGLE_PURPOSE_PRINCIPLE.md`)
governs all audit records generated by Verbatim. Its application to QA work:

- The PQAPS role must verify the principle is enforced at code level (no-export guard,
  purpose-limitation marker, HMAC) and at governance level (records owner and principal
  security and privacy architect sign-off attached to QG-05 evidence) before either gate closes.
- Neither QA Analyst role may authorize a deviation from this principle. Any request to
  use audit records for a purpose not listed in the principle (analytics, benchmarking,
  training, transfer) must be escalated to the principal security and privacy architect.
- This check applies to every increment that touches the audit store, export handlers,
  or the transcript API — not only at gate closure.

## Shared governance rules

1. No promotion gate may be closed by a QA Analyst role alone. The named gate owner (endpoint
   security lead, records/privacy lead, etc.) must accept the evidence.
2. Any finding classified as critical or high by the PQAPS role blocks all merges to `main`
   until resolved — not deferred, not waivedted, not promoted past.
3. The PQAFE NFR gap list (above) must reach zero open items before QG-04, QG-05, and QG-06
   are declared ready for owner review.
4. Both QA Analyst roles must review and countersign any change to the quality gate exit
   criteria before the roadmap version is incremented.
5. Evidence collected by these roles must be retained in `evidence/` under the existing
   versioned evidence structure. No evidence is accepted outside the controlled repository.
