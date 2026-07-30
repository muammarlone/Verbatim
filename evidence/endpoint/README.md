# Endpoint Performance and Capacity Evidence

**Gate:** QG-06 — Endpoint performance, capacity, interruption, full-disk, and recovery matrix  
**Owner:** Endpoint platform lead  
**Status:** OPEN — evidence slots not yet filled  
**Claim boundary:** No throughput, latency, or capacity claim is made until a named endpoint platform lead executes the measurement protocol on the qualified managed endpoint and signs the evidence.

---

## Required evidence slots

| Slot | File | Status |
|---|---|---|
| Short-recording perf run (≤60 s media) | `perf-short.json` | OPEN |
| Long-recording perf run (≥30 min media) | `perf-long.json` | OPEN |
| Interrupted-run recovery | `recovery-interruption.json` | OPEN |
| Full-disk failure behavior | `recovery-full-disk.json` | OPEN |
| Capacity matrix (P50/P95 at spec) | `capacity-matrix.json` | OPEN |
| Batch perf run (25-file max) | `perf-batch.json` | OPEN |

---

## Measurement protocol

### Prerequisites

- Qualified managed Windows endpoint (see QG-03 endpoint specification)
- FFmpeg and FFprobe on `PATH` at approved hashes
- Approved Whisper model at `STS_MODEL_PATH` (hash verified against `sbom/hash-manifest.json`)
- `STS_DATA_DIR` on a volume with at least 20 GiB free
- No other Verbatim jobs running during measurement

### Perf run script

```powershell
cd <repo>
.\.venv\Scripts\python.exe scripts\run_endpoint_perf.py `
    --output evidence\endpoint\perf-short.json
```

For long-recording runs, substitute a synthetic MP4 of the target duration.

### What to record in each slot

Each JSON slot must include (at minimum):

```jsonc
{
  "_schema": "endpoint-perf-evidence/1.0",
  "_status": "filled",
  "date": "YYYY-MM-DD",
  "endpoint_spec": "Windows 11 Pro, Intel i7-1270P, 32 GB RAM, SSD",
  "python_version": "3.11.x",
  "model_id": "<model filename from STS_MODEL_PATH>",
  "media_seconds": 0,
  "wall_seconds": 0,
  "peak_memory_mb": 0,
  "temp_storage_mb": 0,
  "outcome": "complete",
  "claim_boundary": "<30+ char description of what this run proves>"
}
```

### Interruption recovery test

1. Start a long-recording job.
2. Kill the Verbatim process mid-transcription (`Stop-Process`).
3. Restart Verbatim.
4. Confirm the job appears in a terminal failed state (not stuck/running).
5. Confirm no partial audio remains in `STS_DATA_DIR`.
6. Record outcome in `recovery-interruption.json`.

### Full-disk failure test

1. Use a synthetic volume or sparse file to simulate a near-full disk.
2. Start a batch job that will exceed available space.
3. Confirm the job reaches a stable failed state with reason code `BATCH_ITEM_IO_FAILED`.
4. Confirm no partial output files are left in the output folder.
5. Record outcome in `recovery-full-disk.json`.

### Capacity matrix

Measure P50 and P95 wall time and memory for:

| Recording length | Clean audio | Noisy audio |
|---|---|---|
| 5 min | | |
| 30 min | | |
| 60 min | | |
| 4 hr (max) | | |

Record results in `capacity-matrix.json` with the endpoint specification, model ID, and claim boundary.

---

## Negative controls required

At least one run must demonstrate that Verbatim rejects:

1. A recording that exceeds `STS_MAX_MEDIA_SECONDS` with `MEDIA_TOO_LONG`
2. An upload that exceeds `STS_MAX_UPLOAD_BYTES` with `REQUEST_TOO_LARGE`
3. A batch that exceeds `STS_MAX_BATCH_FILES` with `BATCH_FILE_LIMIT_EXCEEDED`

Record the rejection codes in the relevant slot's `negative_controls` array.

---

## Sign-off required

Before QG-06 can be marked `passed`, the endpoint platform lead must:

1. Execute each measurement scenario on the qualified endpoint.
2. Fill each JSON slot with measured values (not estimates).
3. Sign the `capacity-matrix.json` with their name and date.
4. Confirm no unresolved performance or reliability finding remains.

QG-06 cannot be waived. A capacity matrix based on developer-machine measurements does not satisfy this gate.
