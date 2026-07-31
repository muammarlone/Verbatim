# ADR-007: Encrypted Audit Store with Purpose Limitation

- Status: accepted
- Date: 2026-07-30
- Deciders: Principal architect, PQAPS (Privacy and Security QA), records/privacy owner (approval required before implementation)
- Linked stories: STS-123
- Linked gates: QG-03 (encryption), QG-05 (retention and purpose)

## Ground principle

This ADR is governed by the **Audit Single-Purpose Principle**
(`governance/AUDIT_SINGLE_PURPOSE_PRINCIPLE.md`), refined by the principal security and
privacy architect. All design decisions below serve one purpose only:

> Proving that Verbatim processed authorized audio within its stated boundaries so that the
> organization can defend its records-handling practices to authorized auditors, regulators,
> or legal reviewers.

No other use of audit records is permitted. This is a covenant, not a configuration option.
Any implementation detail below that appears to conflict with this principle is resolved in
favour of the principle, not the implementation.

## Context

Verbatim generates a chain of custody linking source audio to transcript exports. Without a
structured, encrypted, purpose-limited audit store, this chain cannot be produced for legal
review, records audits, or regulated workflow defensibility. Three constraints drive the design:

1. **Local-only** (ADR-001): no cloud audit service. The audit store must live on the managed
   endpoint with the same physical security controls as the audio data.
2. **Encryption at rest** (QG-03): all managed data on the endpoint, including audit records,
   must be encrypted before corporate pilot approval.
3. **Purpose limitation** (QG-05, enterprise compliance): audit records exist solely for
   authorized audit queries. They must not be accessible through normal application paths, must
   not be used for analytics, product improvement, or model training, and must not be exported
   alongside transcripts.

## Decision

All transcript derivation trees (STS-123) and structured audit event records are stored in a
dedicated encrypted audit store, physically separate from the application data directory, with
purpose limitation enforced at every access point.

### 1. Separate store directory

| Setting | Default | Notes |
|---------|---------|-------|
| `STS_AUDIT_DIR` | `{STS_DATA_DIR}/.audit/` | Must be outside `STS_DATA_DIR` in production — IT sets this |
| Permissions | Owner-only (700) | Application service identity only; no world/group read |
| Backup exclusion | Recommended | Records owner decides whether audit store is in scope for endpoint backup |

The audit store is never a subdirectory of any batch output folder or export destination.

### 2. Encryption at rest

**Default (managed endpoint):** Windows Data Protection API (`CryptProtectData`/`CryptUnprotectData`)
with the DPAPI machine key or user key as directed by IT. This ties decryption to the provisioned
service identity on the qualified endpoint. Decryption on a different machine or identity fails
closed.

**Enterprise option (IT-managed key):** AES-256-GCM with a 256-bit key stored in Windows
Credential Locker under a named entry controlled by IT. Key rotation requires IT approval and
produces a new encrypted copy of all affected records. The old key is revoked after rotation.

The application never stores encryption keys in source code, environment variables, or managed
data files.

### 3. Derivation tree structure (STS-123)

Each job produces one append-only derivation tree file in the audit store. Records are written
by the audit subsystem only — not by the transcript API, the batch manager, or any export path.

```json
{"record_type": "source",     "job_id": "…", "source_hash": "sha256:…", "size_bytes": 0, "format": "mp4", "duration_seconds": 0.0, "ingested_at": "ISO-8601", "purpose": "audit_only"}
{"record_type": "extraction", "job_id": "…", "ffmpeg_version": "…", "params_hash": "sha256:…", "output_hash": "sha256:…", "extracted_at": "ISO-8601", "purpose": "audit_only"}
{"record_type": "transcription", "job_id": "…", "model_id": "…", "model_hash": "sha256:…", "language": "en", "params_hash": "sha256:…", "segment_count": 0, "transcribed_at": "ISO-8601", "purpose": "audit_only"}
{"record_type": "segment",    "job_id": "…", "index": 0, "start_ms": 0, "end_ms": 0, "text_hash": "sha256:…", "avg_logprob": -0.1, "no_speech_prob": 0.01, "purpose": "audit_only"}
{"record_type": "revision",   "job_id": "…", "revision_id": "…", "segment_index": 0, "operation": "correct", "original_hash": "sha256:…", "corrected_hash": "sha256:…", "revised_at": "ISO-8601", "purpose": "audit_only"}
{"record_type": "export",     "job_id": "…", "format": "json", "destination_scope": "managed_export", "content_hash": "sha256:…", "exported_at": "ISO-8601", "purpose": "audit_only"}
{"record_type": "deletion",   "job_id": "…", "scope": "managed_source_and_derived", "deleted_at": "ISO-8601", "surviving_artifacts": ["audit_tree"], "purpose": "audit_only"}
```

Key properties:
- **Append-only**: file is opened in append mode; no record is modified or deleted on write.
- **Content-free**: transcript text is never stored. Only SHA-256 hashes of text spans.
- **Purpose marker**: every record carries `"purpose": "audit_only"` and
  `"use_restriction": "authorized_audit_query_only"`. These are not runtime enforced alone —
  the access control layer (below) is the enforcement mechanism.
- **HMAC integrity**: each record carries an HMAC-SHA-256 tag computed over the JSON payload
  using the audit store key. Tampered records fail verification.

### 4. Purpose limitation — access control

| Operation | Allowed | Denied |
|-----------|---------|--------|
| Append a new audit record | Audit subsystem only | Transcript API, batch manager, export handler |
| Read a single job's derivation tree | Authorized audit query endpoint only | `/api/jobs/{id}`, `/api/jobs/{id}/export`, batch export |
| Include audit tree in transcript export | Never | Always — TXT/SRT/VTT/MD/JSON exports never contain audit records |
| Use audit records for analytics | Never | Including product telemetry, accuracy measurement, model training |
| Delete a record before retention floor | Never | Application, IT, or operator cannot delete before floor |

The audit query endpoint (`/api/audit/{job_id}/provenance`) is disabled by default
(`STS_AUDIT_QUERY_ENABLED=false`) and requires the same request token as the originating job.
It returns only the decrypted NDJSON derivation tree for audit, not the raw encrypted file.

### 5. Retention

| Setting | Default | Constraint |
|---------|---------|-----------|
| `STS_AUDIT_MIN_RETENTION_DAYS` | 365 | IT-controlled floor; application cannot lower |
| `STS_AUDIT_MAX_RETENTION_DAYS` | 2555 (7 years) | Records owner sets; application enforces ceiling |
| Deletion of managed job | Does not delete audit tree | See `deletion` record above |
| Deletion of audit tree | Only after floor expires; requires explicit IT action | Application never self-deletes |

Retention boundaries are documented to the records/privacy owner as part of QG-05 exit criteria.
The floor and ceiling are not configurable by operators — only IT with named justification.

### 6. Proprietary boundary

The derivation tree is a proprietary internal record of the organization that generated the
transcript. It is not:
- a product artifact delivered to end users,
- an export format accessible through normal UI or API paths,
- usable for benchmarking, training, or product improvement without separate legal authorization,
- transferable to third parties, including Anthropic or any AI provider, as part of any
  telemetry or model-improvement pipeline.

This boundary is enforced by the no-export guard and purpose-limitation marker above, and is
disclosed in the operator manual and records-owner sign-off stub.

## Consequences

- The audit store requires a separate qualified directory, DPAPI or IT-managed key, and named
  records/privacy owner before it can be enabled. It is not active in the synthetic demonstration
  or Codespaces environment.
- `STS_AUDIT_DIR` defaults to a subdirectory that IT must relocate before pilot.
- The PQAPS role must validate HMAC integrity, append-only enforcement, access separation, and
  no-export guard before QG-03 and QG-05 can be declared ready for owner review.
- This ADR supersedes no prior ADR. It extends ADR-003 (storage boundary) with a purpose-limited
  audit layer and extends ADR-001 (local-only) by binding the audit store to the managed endpoint.

## Rejected alternatives

| Alternative | Reason rejected |
|-------------|----------------|
| Inline audit fields in job record | Application can read and overwrite; no separation of concerns |
| Plaintext NDJSON alongside application data | Violates QG-03 encryption requirement |
| Cloud audit service (e.g., Azure Monitor) | Violates ADR-001 local-only principle; audio metadata leaves endpoint |
| SQLite audit database | Not append-only by default; easier to tamper; harder to prove WORM property |
| No structured audit store | Records auditors cannot verify derivation chain; legal defensibility not established |
