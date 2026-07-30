# Export DLP Matrix

**Status:** DRAFT — awaits records and privacy lead review and approval  
**Gate:** QG-05  
**Claim boundary:** This matrix is a draft for lead review; no approved-destination claim exists until the records and privacy lead signs off.

---

## Export formats produced by Verbatim

| Format | Extension | Content | Sensitivity |
|---|---|---|---|
| Plain text | `.txt` | Raw transcript text | Same as source recording |
| SRT subtitles | `.srt` | Timestamped text | Same as source recording |
| VTT captions | `.vtt` | Web-caption text | Same as source recording |
| Markdown | `.md` | Transcript + deterministic analysis notes | Same as source recording + analysis flags |
| JSON | `.json` | Full transcript, segments, model ID, provenance | Same as source recording |

All formats include the spoken content of the recording. The JSON format additionally includes model identity and job provenance. None include the source audio.

---

## Destination approval matrix

**Instructions for records and privacy lead:** mark each cell Approved / Restricted / Prohibited and add conditions.

| Destination | TXT | SRT | VTT | MD | JSON | Conditions |
|---|---|---|---|---|---|---|
| Approved corporate shared drive (DLP-gated) | — | — | — | — | — | Lead to fill |
| DLP-scanned email to internal recipient | — | — | — | — | — | Lead to fill |
| Approved cloud storage (e.g., SharePoint with classification) | — | — | — | — | — | Lead to fill |
| Print (paper copy) | — | — | — | — | — | Lead to fill |
| Personal device or personal email | — | — | — | — | — | Lead to fill |
| External party (contractor, vendor) | — | — | — | — | — | Lead to fill |
| Unapproved public storage | PROHIBITED | PROHIBITED | PROHIBITED | PROHIBITED | PROHIBITED | By policy |

---

## DLP requirements per destination

For each approved destination, the records and privacy lead must confirm:

1. **Classification label** applied to the exported file matches or exceeds the classification of the source recording.
2. **Access control** on the destination limits readers to those authorized for the source recording.
3. **Retention policy** on the destination is at least as restrictive as the source recording's retention obligation.
4. **Deletion obligation** on the destination is documented and owned.

---

## Operator guidance (to be confirmed by lead)

Operators must:

1. Confirm authority to process and export the recording before exporting.
2. Select only approved export destinations.
3. Apply the required classification label to the exported file.
4. Delete the exported copy when the retention obligation expires or the purpose is fulfilled.
5. Report any unauthorized export to the incident contact.

---

## Open items

- [ ] Records and privacy lead to fill destination approval matrix
- [ ] Records and privacy lead to confirm DLP requirements per destination
- [ ] Records and privacy lead to approve operator guidance text
- [ ] Sign off in `evidence/records/sign-off.json`
