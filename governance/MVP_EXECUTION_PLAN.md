# MVP Execution Plan

## Objective

Deliver the smallest controlled capability that proves an authorized user can turn a local MP4 into a useful, reviewable transcript without a cloud service.

## Approved scope

1. Single local operator and loopback web UI.
2. One MP4 per job, with either a single upload or a bounded non-recursive folder batch; one concurrent transcription.
3. Local FFmpeg plus a pre-provisioned Whisper model.
4. Time-linked transcript, lexical search, deterministic review analysis, five exports, batch manifest, and managed-copy deletion.
5. Fixture tests, real single-file and two-file synthetic smoke tests, responsive browser UAT, recorded demonstrations, and explicit residual risks.

## Claim boundary

Approved claims are limited to behavior reproduced by the July 29, 2026 evidence packet. Not approved: production security, regulatory compliance, general accuracy, ROI, speaker attribution, sentiment, autonomous decisions, or multi-user isolation.

## Acceptance gates

- Deterministic guards and state transitions pass automated tests.
- Real synthetic MP4 reaches `complete` through FFmpeg and Whisper within the configured budget.
- Transcript/export provenance resolves to the model artifact and job.
- Deletion removes the scoped job artifacts.
- Batch paths remain inside the configured workspace; existing output files are not overwritten; per-file failures do not conceal successful or failed items.
- UI has no console errors or horizontal overflow at 375, 768, and 1440 px.
- Risks, unsupported claims, runbook, and readiness decision are documented.
