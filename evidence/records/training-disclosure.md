# Operator Training Requirements

**Status:** DRAFT — awaits records and privacy lead review  
**Gate:** QG-05  
**Purpose:** Checklist of training topics that all operators must complete before using Verbatim with corporate recordings.

---

## Required training topics

### 1. Recording authority

- What authorization is required before transcribing a recording?
- Who grants authorization and how is it documented?
- What to do if a recording is inadvertently processed without authority (incident reporting).
- What categories of recording are prohibited (e.g., privileged legal communications, regulated clinical records without appropriate consent).

### 2. Sensitivity classification

- How to determine the sensitivity classification of a recording.
- How to apply the correct classification label to exported files.
- What the classification implies for permitted destinations and handling.

### 3. Approved export destinations

- Which export formats are approved for which destinations (see `export-dlp-matrix.md`).
- How to verify a destination is approved before exporting.
- What to do if a destination is not listed (default: do not export).

### 4. Mandatory deletion

- When managed copies must be deleted (after the authorized purpose is fulfilled).
- How to delete a job and a batch via the Verbatim UI.
- How to confirm deletion is complete.
- How to handle external copies (downloads, batch output): these are outside Verbatim's deletion boundary and must be governed by the operator per the destination's policy.

### 5. Data-handling restrictions

- Do not use Verbatim on a personal device, personal network, or unapproved environment.
- Do not share transcripts with unauthorized recipients.
- Do not process recordings outside the approved use case.
- Do not circumvent consent confirmation.

### 6. Incident reporting

- What constitutes a recordable incident (unauthorized access, accidental export, loss of encrypted device with recordings, etc.).
- Who to contact immediately.
- What information to preserve.

---

## Training delivery options

| Option | Suitability |
|---|---|
| In-person walkthrough with records/privacy lead | Preferred for initial pilot |
| Written self-study with acknowledgement sign-off | Acceptable with lead approval |
| LMS module (if organization has one) | Lead must approve module content |

---

## Acknowledgement requirement

Each operator must sign or acknowledge training completion before accessing corporate recordings through Verbatim. The acknowledgement must record:

- Operator name
- Date of training
- Training format
- Trainer or approver name

---

## Open items

- [ ] Records and privacy lead to review and approve topic list
- [ ] Records and privacy lead to approve delivery format for pilot
- [ ] Records and privacy lead to confirm acknowledgement process
- [ ] Training acknowledgements collected for all pilot operators before first corporate recording
- [ ] Sign off in `evidence/records/sign-off.json`
