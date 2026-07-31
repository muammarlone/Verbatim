# Deletion Drill Procedure — Verbatim STS

Version: 1.0 | Generated: 2026-07-30 | Author: Virtual AI — Information Security Officer

## Purpose

Verify that job deletion removes source media and transcript from disk while the audit
derivation tree (DT-03) survives with a deletion record appended. This drill is a required
recurring check per the operator checklist and is a QG-05 exit criterion.

## Pre-conditions

- Dev or test instance of Verbatim STS running locally
- At least one completed job with a transcript
- STS-123 AuditStore implemented and wired into JobProcessor
- STS_AUDIT_DIR set to a directory writable by the test process
- STS_AUDIT_QUERY_ENABLED=true on test instance (required for step 5 verification)

## Procedure

### Step 1 — Record baseline

1. Note `job_id` of target job.
2. Record path of source file: `{STS_DATA_DIR}/jobs/{job_id}/source.*`
3. Record path of transcript: `{STS_DATA_DIR}/jobs/{job_id}/transcript.json`
4. Record path of audit tree: `{STS_AUDIT_DIR}/{job_id}.audit.ndjson`
5. Confirm all three files exist before proceeding.

```
# Example verification
ls {STS_DATA_DIR}/jobs/{job_id}/
ls {STS_AUDIT_DIR}/{job_id}.audit.ndjson
```

### Step 2 — Execute deletion

Via API:
```
DELETE /api/jobs/{job_id}
```

Or via UI: Jobs list → Delete button → Confirm dialog.

Expected HTTP response: `200 OK` with `{"deleted": true}` or equivalent.

### Step 3 — Verify source and transcript removed

- `{STS_DATA_DIR}/jobs/{job_id}/` directory should not exist or should be empty.
- PASS: source file gone, transcript file gone.
- FAIL: either file remains on disk.

```
# Should return "not found" or empty
ls {STS_DATA_DIR}/jobs/{job_id}/
```

### Step 4 — Verify audit tree survives

- `{STS_AUDIT_DIR}/{job_id}.audit.ndjson` MUST still exist.
- PASS: file exists and is non-empty.
- FAIL: file deleted or missing.

```
ls {STS_AUDIT_DIR}/{job_id}.audit.ndjson
```

### Step 5 — Verify deletion record in audit tree

Read provenance via API (requires STS_AUDIT_QUERY_ENABLED=true on test instance):

```
GET /api/audit/{job_id}/provenance
```

Or via test script:

```python
from src.secure_transcribe.audit_store import AuditStore
store = AuditStore()
records = store.read_provenance(job_id)
deletion_records = [r for r in records if r.get("record_type") == "deletion"]
assert len(deletion_records) >= 1, "No deletion record found"
assert deletion_records[0]["purpose"] == "audit_only"
```

- PASS: at least one record with `record_type == "deletion"` present.
- PASS: deletion record contains `purpose: "audit_only"` and valid HMAC.
- FAIL: no deletion record, or HMAC verification fails.

### Step 6 — Verify retention floor

For a new audit tree (job less than 365 days old):

```python
from src.secure_transcribe.audit_store import AuditStore
store = AuditStore()
assert store.retention_floor_reached(job_id, min_days=365) == False, \
    "Retention floor should not be reached for a new job"
```

- PASS: `retention_floor_reached()` returns False for a job created today.
- FAIL: floor check absent, bypassed, or returns True incorrectly.

## Pass/Fail Summary

| Check | Expected | Pass Condition |
|-------|----------|----------------|
| Source file deleted | Gone | File not found at path |
| Transcript deleted | Gone | File not found at path |
| Audit tree survives | Exists | File exists, non-empty |
| Deletion record appended | Present | `record_type == "deletion"` in provenance |
| HMAC valid | Valid | `read_provenance()` does not raise HMAC error |
| Retention floor enforced | Not yet reached | `retention_floor_reached()` returns False for new job |

## Recording drill results

After each drill run, record the following in the evidence index or a dated drill log:

- Date and time of drill
- Job ID used (redact if from production data)
- Tester name/role
- Pass/Fail for each check
- Any deviations or defects found
- Defect tracking reference if any check failed

## Gap

This drill requires STS-123 (AuditStore) to be implemented and merged. Until STS-123 is
complete, steps 4–6 cannot be verified. The drill is mandatory before QG-05 can be declared
passed. Status: BLOCKED on STS-123.
