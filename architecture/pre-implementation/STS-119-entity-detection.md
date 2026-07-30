# STS-119 Pre-Implementation Requirements: Sensitive Entity Detection (PHI/PII/BHI/BII)

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized operator, I can receive a sensitive-entity flag report alongside each
transcript that identifies PHI, PII, BHI, and BII candidate spans with category labels and
confidence scores.

## Blocking conditions (all must be satisfied before implementation begins)

1. **Privacy threat model required**: A written threat model covering:
   - False-positive risk: legitimate content flagged as PHI — what is the reviewer's burden?
   - False-negative risk: PHI/PII missed — what is disclosed to operators about this risk?
   - Model privacy: does the NLP model itself process or retain personal data during inference?
   - Co-export risk: does the flag report travel alongside the transcript to downstream systems?
   - Deletion: are flag reports deleted on job deletion per R-08?

2. **Approved NLP approach required**: An ADR documenting:
   - Chosen library (e.g., spaCy, Presidio, GLiNER, Hugging Face NER) — local inference only
   - Model weight provenance and SHA-256 in sbom/hash-manifest.json
   - Supported category definitions: what exactly constitutes PHI, PII, BHI, BII in this context
   - False-positive and threshold trade-offs disclosed to operators

3. **Privacy lead approval required**: The entity detection approach must be reviewed by
   a privacy lead before implementation, not after. The privacy lead must approve:
   - Category taxonomy (PHI, PII, BHI, BII definitions for the organization's context)
   - Threshold defaults and operator override bounds
   - Disclosure text shown to operators about detection limitations

4. **Owner required**: A named privacy lead must accept ownership of the detection design.

5. **STS-120 dependency**: Redaction (STS-120) must not be implemented before STS-119 is complete
   and reviewed, to ensure the original transcript preservation contract is correct.

## Acceptance evidence (when blocked conditions are cleared)

- Privacy threat model with privacy lead sign-off
- Approved NLP approach ADR with supply chain
- Entity detection runs locally with no cloud call
- Flag report co-exported only with reviewer approval, not automatically
- Deletion propagation test for flag reports
- False-positive/false-negative disclosure documented in UI and features doc

## Linked

- Linked stories: STS-120 (redaction, depends on this)
- Linked risk: R-05, R-06, R-08
- Linked gate: QG-01 (domain eval lead), QG-04 (records disposition)

## Claim boundary

ASSUMPTION: No entity detection is implemented. No PHI, PII, BHI, or BII spans are
identified, stored, or reported. This stub records preconditions only.
No partial implementation is authorized before conditions 1–5 are met.
