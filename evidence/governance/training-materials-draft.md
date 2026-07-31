# Data Handling Training — Verbatim STS Operator

Version: 1.0 (draft) | Generated: 2026-07-30 | Author: Virtual AI — Information Security Officer

**STATUS: DRAFT — pending records owner review and approval by DPO (muammarlone@gmail.com).
Final training materials require DPO approval before deployment to operators.**

---

## Audience

Verbatim STS operators: staff who upload, transcribe, review, and export recordings on the
managed corporate endpoint.

---

## Core principles

### 1. Source files are confidential

Treat all uploaded media as confidential. Do not copy source audio or video files to:
- personal drives or home directories,
- external storage devices (USB, external drives),
- cloud services not approved by IT,
- email or messaging platforms.

Source files must remain in the managed STS data directory at all times.

### 2. Transcripts are confidential

Exported transcripts (TXT, SRT, VTT, JSON) contain the content of your recordings and must be
handled per your organization's document classification policy. Apply the same controls you
would to the original recording.

Transcripts may contain protected health information (PHI), personally identifiable information
(PII), behavioral health information (BHI), or business-sensitive information (BII) depending
on the source audio. Review exports before distributing them.

### 3. The audit tree is restricted — never attempt to export it

The audit derivation tree exists solely to prove that Verbatim processed audio within its
stated boundaries. It is stored encrypted by the system, is never visible in the export UI,
and cannot be accessed through normal application paths.

If you are asked to provide audit records for a legal hold, records audit, or regulatory
inspection, contact the Data Protection Officer. Do not attempt to find or copy audit files
directly from the file system.

### 4. Delete jobs when no longer needed

Use the Delete button in the Jobs list to remove a job. Deletion removes the source file and
transcript from disk. The audit record survives for the retention period — this is by design
and required for defensibility.

Do not keep jobs indefinitely. Your organization's records policy governs how long transcripts
should be retained before deletion.

### 5. Do not manipulate files in the data directory directly

Use the application UI or API only. Direct file manipulation (copying, moving, renaming,
deleting files in STS_DATA_DIR or STS_AUDIT_DIR) bypasses the audit trail and may corrupt
the job state. If you need to move data, contact IT.

### 6. Do not share application credentials or job links

Job access is scoped to the authenticated user on the managed endpoint. Do not share session
tokens, job IDs combined with direct file paths, or any mechanism that would allow access to
jobs outside the application's authorization controls.

---

## What the system retains after job deletion

| Item | Retained after deletion? | Where | Who can access |
|------|--------------------------|-------|----------------|
| Source media | No | Removed on Delete | N/A |
| Transcript | No | Removed on Delete | N/A |
| Job metadata | No | Removed on Delete | N/A |
| Audit derivation tree | Yes — minimum 365 days | Encrypted audit directory | Authorized audit queries only (requires DPO authorization) |

---

## What to do if something looks wrong

| Situation | Action |
|-----------|--------|
| Cannot delete a job | Contact system administrator |
| Unexpected files in data directory | Do not move or delete them; contact IT |
| Error about audit store or HMAC | Contact system administrator; do not ignore or retry repeatedly |
| Request to export audit records | Contact DPO before taking any action |
| Suspected data breach or unauthorized access | Follow your organization's incident response procedure immediately |

---

## Knowledge check (to be completed after training)

Before being authorized to operate Verbatim STS with real recordings, operators must confirm
understanding of the following:

- [ ] I will not copy source files or transcripts to unapproved storage or services.
- [ ] I understand transcripts may contain PHI/PII and will handle exports accordingly.
- [ ] I will not attempt to locate or copy audit tree files from the file system.
- [ ] I will delete jobs when no longer required per the organization's records policy.
- [ ] I will contact IT or the DPO if I encounter unexpected system behavior.

Operator name: ___________________________
Date: ___________________________
Supervisor sign-off: ___________________________
