# STS-101 Pre-Implementation Requirements: Speaker Diarization

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: Add speaker diarization with measured evaluation.

## Blocking conditions (all must be satisfied before implementation begins)

1. **Library decision required**: An ADR must document the chosen diarization library
   (e.g., pyannote.audio, nemo, whisperx diarization), covering:
   - License compatibility with corporate use (pyannote requires token/license agreement)
   - Model weight provenance and supply chain: SHA-256 must be recorded in sbom/hash-manifest.json
   - Privacy implications of speaker embedding models (do they identify individuals?)
   - Memory and runtime budget on the target hardware (R-05 constraint)
   - Whether model inference is purely local with no external calls

2. **Privacy threat model required**: A written threat model covering:
   - Whether speaker embeddings can be used to re-identify speakers across sessions
   - What is retained: embeddings, labels, cluster metadata
   - Deletion: are embeddings deleted on job deletion per R-08?
   - Export: are embeddings included in any export format?

3. **Evaluation dataset required**: A held-out diarization set with:
   - Provenance documentation (who created it, consent status, synthetic vs. real)
   - Subgroup labels (number of speakers, noise level, overlap density)
   - Domain evaluation lead approval before use in any accuracy claim

4. **Owner required**: A named domain evaluation lead must accept ownership of the diarization
   accuracy evaluation before implementation begins.

5. **QG-01 prerequisite**: Domain accuracy evaluation (QG-01) for transcription must be
   in progress before adding diarization claims on top.

## Acceptance evidence (when blocked conditions are cleared)

- Library ADR with supply chain and privacy review
- Held-out diarization set with approved dataset card
- Subgroup report by speaker count, noise level, overlap density
- Deletion propagation test for diarization embeddings
- No external network call during diarization inference

## Linked

- Linked risk: R-05
- Linked gate: QG-01 (domain eval lead approval)

## Claim boundary

ASSUMPTION: Speaker diarization is not implemented. No diarization results are produced,
stored, or exported. This stub records the preconditions; no partial implementation
is authorized before conditions 1–5 are met.
