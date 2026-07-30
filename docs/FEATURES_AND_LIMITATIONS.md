# Features and Limitations

This reference states what Verbatim 0.2.0 can do today, what is available only for
controlled contract testing, and what remains backlog work. It is the claim boundary for
the user manual and explainer video.

## Capability status

| Capability | Status | Evidence boundary |
|---|---|---|
| Single-file validation, local transcription, review, export, and deletion (MP4, M4A, MP3, WAV, AAC, FLAC, OGG, WMA) | Demonstrated | One synthetic 9.193-second English MP4 fixture; exact 17-word match is not a general accuracy claim |
| Multi-format audio support: M4A, MP3, WAV, AAC, FLAC, OGG, WMA alongside MP4 | Tested and demonstrated | Magic-byte validation per format; SUPPORTED_MEDIA_EXTENSIONS constant; 21 security tests; no domain accuracy claim |
| Per-segment transcription confidence indicators (avg_logprob, no_speech_prob) | Tested and demonstrated | Whisper fields captured and surfaced in UI; color badge per segment; interpretation requires human judgment |
| Non-recursive folder-to-folder batch, up to 25 media files and five output formats | Demonstrated | One controlled two-file synthetic batch plus one real three-file dev-machine run (24.6 MB, 140 s, 0 failures); not a throughput or corporate-endpoint claim |
| Time-linked transcript search and local media seek | Demonstrated | Browser UAT and narrated synthetic recording |
| Rule-based review aids | Demonstrated | Deterministic extraction only; no semantic or professional judgment claim |
| TXT, Markdown, SRT, VTT, and JSON export | Tested and demonstrated | Destination governance remains external to Verbatim |
| Explicit single-job and managed-batch cleanup | Tested and demonstrated | External exports, original batch inputs, backups, and indexes remain outside the deletion boundary |
| Bounded CSV/XLSX protected-recording manifest preview | Backend contract only; disabled by default | Parsing and redaction tests only; no UI, credential resolution, acquisition, or execution |
| Password-protected ZIP/7z extraction | Not available | Backlog STS-108; the enable flag is a hard stop gate; threat model and ADR-006 pre-implementation requirements must be met |
| Microsoft Teams / Microsoft Graph recording connector | Not available — Roadmap Phase 3A | Backlog STS-121; requires Azure AD app registration, ADR-006 per-platform threat model, and Phase 1 gate clearance |
| Zoom Cloud OAuth/PKCE recording connector | Not available — Roadmap Phase 3B | Backlog STS-122; requires Zoom Marketplace vendor approval, ADR-006 per-platform threat model, and Phase 1 gate clearance |
| Signed installer, qualified container, or production deployment package | Not available | Wheel build passes, but deployment qualification and full transitive audit remain open |
| Multi-user access, roles, or remote hosting | Not supported | Architecture is single-user and loopback-only |
| Compliance, legal-record, ROI, or general accuracy certification | Not claimed | Requires organizational and domain-specific evaluation outside this repository |

## Strengths

- **Data locality:** media processing and the model are local; the product contains no cloud
  transcription call or silent model download.
- **Reviewability:** transcript segments link to the source video, so an operator can check
  meaning instead of treating generated text as authoritative.
- **Deterministic controls:** authorization, byte and duration budgets, path containment,
  no-overwrite export, retention sweep, and state transitions are enforced in code.
- **Bounded failure:** FFmpeg and Whisper have timeouts; folder files fail independently;
  stable reason codes make support and regression testing repeatable.
- **Portable outputs:** text, caption, review-note, and evidence formats cover common handoff
  needs without a proprietary cloud account.
- **Evidence honesty:** synthetic fixtures, measured wall times, accelerated playback, and
  residual risks are disclosed instead of converted into broad quality claims.

## Trade-offs and weaknesses

- **Local processing consumes endpoint resources.** CPU-only Whisper can be slow and screen
  recording itself increased the measured demo runtime. Hardware-specific throughput must
  be qualified before a pilot.
- **Local-first is not the same as access isolation.** Anyone with the same OS identity or
  data-directory access may read managed media and text. IT-owned ACL, encryption, egress,
  endpoint protection, and backup exclusions remain required.
- **Transcription quality is input-dependent.** The exact synthetic fixture result says
  nothing about accents, languages, noise, overlapping speakers, or specialist vocabulary.
- **Analysis is intentionally narrow.** Keyword and structural cues are explainable and
  repeatable, but they can miss context or overemphasize superficial language.
- **Exports leave the managed boundary.** Verbatim cannot delete or govern copies placed in
  email, shared drives, backups, indexes, or downstream tools.
- **The service is single-user.** Loopback binding and a page token reduce accidental local
  access; they do not provide enterprise identity, authorization roles, or tenant isolation.
- **Deployment is not production-qualified.** Signed installation, SBOM, full transitive
  dependency audit, Windows matrix, rollback, penetration, and accessibility gates remain open.
- **Protected and Zoom recordings are not executable features.** Only a disabled, bounded,
  secret-target-redacted manifest preview contract exists.

## Why the product uses these boundaries

Verbatim prioritizes inspectable local behavior over convenience that would silently widen
the trust boundary. A fixed local model avoids cloud transfer but moves capacity and patching
responsibility to the endpoint. No-overwrite export prevents accidental data loss but requires
an empty destination. Explicit deletion makes intent visible but cannot reach copies outside
the managed tree. Disabled connector flags allow contract work to land without implying that
credentials or remote acquisition are safe.

The result is suitable for controlled synthetic demonstrations and, after named approvals,
a narrow internal pilot. It is not yet a production or regulated-records platform.

## Quality definition

"100% quality" is not a defensible product claim. Quality is treated as a set of measurable
gates: functional regression, branch coverage, architecture checks, dependency review,
browser UAT, accessibility, security testing, realistic domain evaluation, deployment
qualification, and residual-risk ownership. A gate that has not run remains open; it is not
converted into a pass by documentation or demo polish.

Current reproducible evidence is indexed in [evidence/README.md](../evidence/README.md).
Open release conditions are tracked in the
[readiness report](../governance/READINESS_REPORT.md) and
[risk register](../governance/RISK_REGISTER.md).
