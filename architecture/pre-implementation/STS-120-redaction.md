# STS-120 Pre-Implementation Requirements: Transcript Redaction

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized operator, I can request redaction of sensitive-entity spans in
exported transcripts, replacing flagged content with typed placeholder tokens.

## Blocking conditions (all must be satisfied before implementation begins)

1. **STS-119 must be complete and reviewed**: Redaction cannot be designed before the entity
   detection taxonomy, thresholds, and privacy lead approvals from STS-119 are finalized.
   Redaction scope depends directly on what STS-119 defines as flaggable content.

2. **Records disposition approval required (QG-04)**: Redaction creates a new derived artifact
   (redacted export) that is distinct from the original transcript. The records disposition
   policy must define:
   - Is the redacted export a separate record requiring its own retention policy?
   - Who may authorize a redaction run? (Must be reviewer-approved, not automatic)
   - What audit event documents each redaction run?
   - What happens when the redacted copy is deleted?

3. **Original-preservation contract required**: A design document specifying:
   - The original transcript is never modified by redaction (only the export is)
   - The original is stored separately from the redacted export
   - The redacted export is clearly labeled and distinguishable in UI and file system
   - A reviewer must explicitly approve each redaction before export

4. **Threat model required**: A written threat model covering:
   - Partial redaction: what if a reviewer selects a span that is too narrow, leaving PII?
   - Disclosure via placeholder token: can the token shape reveal the original content?
   - Downstream distribution: what controls prevent a redacted export from being treated
     as the authoritative transcript?

5. **Owner required**: A named privacy lead and records officer must both approve the redaction
   design before implementation.

## Acceptance evidence (when blocked conditions are cleared)

- Original transcript unchanged after redaction run
- Redacted export clearly labeled in UI and audit log
- Reviewer-approval gate before each redaction export
- Deletion of redacted copy tracked in audit log separately from original
- Redaction scope and limitations disclosed in UI and features doc

## Linked

- Linked stories: STS-119 (entity detection, prerequisite)
- Linked risk: R-06, R-07, R-08
- Linked gate: QG-04 (records disposition approval)

## Claim boundary

ASSUMPTION: No redaction capability is implemented. Original transcripts are always
complete and unmodified. This stub records preconditions only.
No partial implementation is authorized before conditions 1–5 are met.
