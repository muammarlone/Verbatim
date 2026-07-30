# Principal Architect Quality Hardening Assessment

## Decision

Verbatim remains **proceed with conditions** for a controlled synthetic demonstration.
The current increment improves truthfulness, operability, and reproducibility; it does not
change the production or corporate-pilot approval boundary.

Absolute "100% quality" is not an auditable state. Release quality is defined by named gates
with evidence, owners, thresholds, and residual risk. An unrun gate stays open.

## Current strengths

1. Deterministic privacy, consent, path, byte, duration, timeout, no-overwrite, deletion,
   and state-transition controls are implemented and covered by regressions.
2. Real local FFmpeg and Whisper processing has controlled synthetic evidence for single and
   two-file paths.
3. L1-L3 architecture, decisions, risks, backlog, evaluation catalog, and evidence are linked.
4. UI language separates rule-based review assistance from human judgment.
5. The protected-recording foundation stops at a disabled, redacted, expiring preview plan.

## Ranked hardening queue

| Priority | Weakness | User or enterprise impact | Required exit evidence |
|---|---|---|---|
| P1 | No representative domain transcription evaluation | Consequential transcript errors may be missed | Approved multilingual/noise/domain set, word/error measures, human meaning review, model/version provenance |
| P1 | Deployment supply chain is not qualified | Installation may introduce vulnerable or unapproved components | Full transitive audit or approved alternative, SBOM, signed package, Windows matrix, rollback test |
| P1 | Same-OS-user access is outside application authorization | Local media and text may be readable by an unintended local principal | Service identity design, ACL test, encryption/backup/index policy, penetration review |
| P1 | Accessibility and penetration gates are incomplete | Keyboard, assistive-technology, or security failures could block pilot users | Automated and manual WCAG-oriented UAT, screen reader path, contrast evidence, scoped penetration report |
| P1 | Export and backup deletion are outside the managed tree | Users may believe deletion removed all copies | Records training, destination DLP/retention controls, visible copy-boundary acceptance evidence |
| P2 | CPU/storage performance is qualified on one host only | Other endpoints may miss time and capacity expectations | Approved hardware matrix, concurrent workload profile, disk-full and long-media recovery evidence |
| P2 | Manifest UI, credential providers, archive extraction, and Zoom retrieval are absent | Protected recordings cannot be processed | Separate ADRs, threat models, provider lifecycle tests, hostile archive corpus, OAuth/host allowlist tests, accessible UI UAT |
| P2 | Documentation and demonstration claims can drift from machine evidence | Reviewers may act on stale counts or hashes | Deterministic product-evidence validator in regression and release commands |

## This increment closes

- A user manual covering installation, single and batch use, review, export, deletion,
  troubleshooting, configuration, and safe operation.
- A capability reference that marks demonstrated, contract-only, unavailable, unsupported,
  and not-claimed areas.
- A reproducible 10-scene explainer with source hashes, final hash, poster, contact sheet,
  consistent narration, and explicit claim boundaries.
- A deterministic validator for documentation links, capability language, video/source
  hashes, stream metadata, metric alignment, and required claim-boundary phrases.

## Residual decision

No honest principal architect should label the product production-ready until all P1 gates
have named owners and passing evidence. The next bounded implementation slice should be
deployment supply-chain qualification or representative domain evaluation; connector work
should not outrun those trust gates.

## Follow-up principal architect review

STS-116 converts this assessment into a versioned eight-gate roadmap and a fail-closed
promotion validator. The decision remains `proceed_with_conditions`, with QG-01 through
QG-06 blocking a corporate pilot.

This increment materially reduced locally controllable risk:

- fixed dark-theme contrast for action, danger, and processing states;
- restored mobile access to system readiness;
- added arrow-key tab navigation and named dialog/media/progress semantics;
- added COOP, CORP, and legacy cross-domain deny headers;
- passed four responsive light/dark Chromium cases with no overflow, console errors, or
  unexpected requests;
- generated a matching direct-pin SBOM and advisory report; and
- bound roadmap, browser, dependency, source, documentation, and release evidence to
  deterministic validators.

The remaining blockers need accountable corporate owners or qualified human evidence; code
changes alone cannot close them. The authoritative execution order, owner roles, and exit
criteria are in [QUALITY_ROADMAP.md](QUALITY_ROADMAP.md).
