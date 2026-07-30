# Deletion Drill Guide

**Status:** DRAFT — awaits records and privacy lead review  
**Gate:** QG-05  
**Purpose:** Step-by-step guide for the records and privacy lead to witness or verify a full deletion cycle.

---

## What Verbatim deletes vs. what it does not

| Item | Verbatim deletes? | Owner of deletion |
|---|---|---|
| Source audio (working copy in `STS_DATA_DIR`) | Yes — on job delete | Operator via UI |
| Extracted mono audio (temporary working file) | Yes — immediately after transcription | Automatic |
| Transcript and analysis records in `STS_DATA_DIR` | Yes — on job delete | Operator via UI |
| Batch-managed MP4 copies | Yes — on batch delete | Operator via UI |
| Batch output folder (TXT, SRT, etc.) | **No** — operator must manage separately | Operator per records policy |
| Browser-downloaded exports | **No** — outside Verbatim boundary | Operator per records policy |
| Original source files (input folder for batches) | **No** — never touched | Operator per records policy |
| Audit log events | **No** — audit log is append-only | Records lead per retention policy |

---

## Pre-drill checklist

Before running the drill:

- [ ] Verbatim is running on the qualified managed endpoint
- [ ] A synthetic or explicitly authorized low-risk recording is available
- [ ] `STS_DATA_DIR` path is confirmed
- [ ] Records and privacy lead (or designated witness) is present

---

## Drill A: Single-job deletion

1. Upload a synthetic MP4 via the Verbatim UI.
2. Confirm the job completes and the transcript appears.
3. Export to at least one format (TXT recommended) via the browser.
4. Note the exported file location in the downloads folder.
5. In the Verbatim UI, select the job and choose **Delete permanently**.
6. Confirm the deletion dialog and wait for the job to disappear from the list.

**Verify:**

- [ ] The job no longer appears in **Recent recordings**.
- [ ] `GET /api/jobs/<job_id>` returns 404.
- [ ] The source MP4 and working audio are absent from `STS_DATA_DIR`.
- [ ] The transcript and analysis JSON are absent from `STS_DATA_DIR`.
- [ ] The browser-downloaded TXT file is still present in the downloads folder (not deleted by Verbatim).
- [ ] The audit log at `STS_DATA_DIR/audit/events.jsonl` contains a `job_deleted` event with the job ID.

Record outcome in `evidence/records/sign-off.json` under `deletion_drill_single_job`.

---

## Drill B: Batch managed-copy deletion

1. Place two synthetic MP4 files in a batch input folder.
2. Run a folder batch from the Verbatim UI with TXT output.
3. Confirm both files complete.
4. Note the output TXT files in the output folder.
5. In the Verbatim UI, select the batch and choose **Remove managed copies**.
6. Confirm the managed-copy removal and wait for the batch to disappear.

**Verify:**

- [ ] The batch no longer appears in the Verbatim UI.
- [ ] `GET /api/batches/<batch_id>` returns 404.
- [ ] The batch-managed MP4 copies are absent from `STS_DATA_DIR`.
- [ ] The original input MP4 files are still present in the batch input folder (not deleted by Verbatim).
- [ ] The output TXT files are still present in the batch output folder (not deleted by Verbatim).
- [ ] The audit log contains `batch_deleted` events for both jobs.

Record outcome in `evidence/records/sign-off.json` under `deletion_drill_batch`.

---

## Drill C: Retention sweep

1. Set `STS_RETENTION_DAYS=0` in a test environment.
2. Restart Verbatim.
3. Confirm all jobs older than 0 days have been swept from `STS_DATA_DIR`.
4. Confirm sweep events appear in the audit log.

Record outcome in `evidence/records/sign-off.json` under `deletion_drill_retention_sweep`.

---

## Audit log review

The audit log is at `STS_DATA_DIR/audit/events.jsonl`. Each line is a JSON object with:

- `event`: event type (e.g., `job_deleted`, `batch_deleted`, `retention_swept`)
- `job_id` or `batch_id`
- `timestamp`

The audit log does not contain transcript content, recording audio, or secret values.

**Verify:**
- [ ] `job_deleted` events are present for Drill A jobs.
- [ ] `batch_deleted` events are present for Drill B batch.
- [ ] No secret values, audio bytes, or transcript text appear in the audit log.

---

## Open items

- [ ] Records and privacy lead to witness Drills A, B, C
- [ ] Records and privacy lead to verify each checklist item
- [ ] Records and privacy lead to sign off in `evidence/records/sign-off.json`
