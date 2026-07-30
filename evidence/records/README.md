# Records and Privacy Evidence

**Gate:** QG-05 — Export destination, DLP, retention, training, and deletion-drill acceptance  
**Owner:** Records and privacy lead  
**Status:** OPEN — evidence slots not yet filled; sign-off not yet obtained  
**Claim boundary:** No privacy compliance, records-compliance, DLP, or retention claim is made until the records and privacy lead has reviewed and signed each slot.

---

## Required sign-off items

| Item | Document | Status |
|---|---|---|
| Export destination approval | `export-dlp-matrix.md` | DRAFT — awaits lead review |
| Retention and deletion drill | `deletion-drill-guide.md` | DRAFT — awaits lead review |
| Operator training requirements | `training-disclosure.md` | DRAFT — awaits lead review |
| Records lead sign-off | `sign-off.json` | OPEN |

---

## What the records and privacy lead must review

### Export destinations

Each export format (TXT, SRT, VTT, MD, JSON) produces a file that leaves Verbatim's managed boundary. The lead must:

1. Approve or restrict each format for each intended destination (shared drive, DLP-gated email, approved cloud, print, etc.).
2. Confirm that the DLP policy on each destination applies at least the same sensitivity classification as the source recording.
3. Confirm that operator training covers the approved destinations and prohibited ones.

See `export-dlp-matrix.md` for the draft matrix.

### Retention

The lead must:

1. Approve the default retention period (`STS_RETENTION_DAYS`, default 7 days) or specify a project-specific value.
2. Confirm that the automated sweep (runs at startup) is sufficient for the retention obligation, or require a scheduled sweep.
3. Confirm that external copies (browser downloads, batch output folder) are covered by the destination's retention policy, not by Verbatim's deletion boundary.
4. Confirm backup exclusion: Verbatim's `STS_DATA_DIR` must not be included in endpoint backup if recordings are subject to hold or deletion obligation.

### Deletion drill

The lead must witness or verify a full deletion cycle:

1. Single-job deletion through the Verbatim UI.
2. Batch managed-copy deletion through the Verbatim UI.
3. Audit log review confirming deletion events are present.
4. Confirmation that the original source files and the batch output folder files are NOT deleted by Verbatim (by design).
5. Confirmation that browser-downloaded exports are not deleted by Verbatim (operator must manage separately).

See `deletion-drill-guide.md` for the step-by-step.

### Training

The lead must confirm that operators receive training on:

1. Recording authority: who is authorized to transcribe which recordings.
2. Approved export destinations and sensitivity handling.
3. Mandatory deletion after processing.
4. Incident reporting if a recording is processed without authority.

See `training-disclosure.md` for the requirements checklist.

---

## Sign-off JSON (fill when ready)

When all items are reviewed and accepted, the records and privacy lead fills `sign-off.json`:

```jsonc
{
  "_schema": "records-privacy-sign-off/1.0",
  "_status": "filled",
  "date": "YYYY-MM-DD",
  "lead_name": "<Records and Privacy Lead name>",
  "retention_days_approved": 7,
  "approved_export_destinations": ["<destination 1>", "<destination 2>"],
  "backup_exclusion_confirmed": true,
  "deletion_drill_witnessed": true,
  "operator_training_approved": true,
  "open_findings": [],
  "claim_boundary": "Records and privacy lead has reviewed and accepted the Verbatim retention, deletion, export, and training controls for the named pilot scope."
}
```

QG-05 cannot be waived. A self-certification by the operator does not satisfy this gate.
