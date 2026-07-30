# Principal Architect Quality Roadmap

## Promotion decision

Verbatim is suitable for a controlled synthetic demonstration and is **not yet ready for a
corporate pilot**. Six promotion-blocking gates remain open. The authoritative state is
[the machine-readable roadmap](../evals/quality-roadmap.json), and the generated
[quality-gate report](../evidence/quality/quality-gate-report.json) must agree with it.

“100% quality” is not a release state. The zero-compromise target is: every applicable
promotion gate passes with reproducible evidence, an accountable owner, an accepted
threshold, and an explicit residual-risk decision. Missing or stale evidence blocks promotion.

## Current gate state

| Gate | Outcome required | Owner role | State | Pilot blocking |
|---|---|---|---|---|
| QG-01 | Representative transcription quality by language, noise, speaker, and domain | Domain evaluation lead | blocked | yes |
| QG-02 | Full dependency, signed installer, upgrade, uninstall, and rollback qualification | IT packaging and security lead | partial | yes |
| QG-03 | OS identity, ACL, encryption, backup, recovery, and penetration acceptance | Endpoint security lead | blocked | yes |
| QG-04 | Automated plus manual accessibility and application-security acceptance | Accessibility and application security lead | partial | yes |
| QG-05 | Export destination, DLP, retention, training, and deletion-drill acceptance | Records and privacy lead | partial | yes |
| QG-06 | Endpoint performance, capacity, interruption, full-disk, and recovery matrix | Endpoint platform lead | partial | yes |
| QG-07 | Credential, protected archive, and Zoom connector qualification | Connector security lead | blocked | no for the local-only pilot |
| QG-08 | Truthful evidence and fail-closed promotion control | Release governance lead | passed | yes |

The `partial` state means useful evidence exists but the exit criteria are not satisfied. It
does not grant pilot approval.

## Execution sequence

### Phase 1: trust baseline

1. Assign named people to the six promotion-blocking owner roles and approve their evidence
   protocols before collecting results.
2. Run STS-104 on an approved sealed dataset. Record model hash, dataset version, subgroup
   measures, meaning-impact review, threshold, variance, failures, and human acceptance.
3. Build the approved offline wheelhouse and signed Windows package. Produce the full
   transitive SBOM, vulnerability disposition, package/model/media-tool hashes, and clean-
   machine install, repair, upgrade, uninstall, and rollback evidence.
4. Test the chosen service identity, storage ACL, encryption, backup exclusion, indexing,
   recovery, and deletion propagation on a managed endpoint. Complete scoped penetration
   testing with no unresolved critical or high findings.
5. Execute keyboard-only and supported screen-reader workflows on the approved browser
   matrix. Re-run automated responsive, contrast, header, overflow, console, and egress checks.
6. Approve export destinations, retention/DLP rules, operator training, and deletion/recovery
   drills with records and privacy owners.

Phase 1 exits only when QG-01 through QG-06 and QG-08 are `passed` and their evidence hashes
resolve. A waiver cannot replace identity isolation, authorization, truthful reporting, or an
unresolved critical security finding.

### Phase 2: environment qualification

1. Define minimum and recommended Windows endpoint profiles.
2. Measure P50/P95 processing time, CPU, memory, temporary storage, output storage, timeout,
   and failure rates for short, long, clean, noisy, and interrupted synthetic cases.
3. Drill full-disk, process termination, restart, partial batch, unavailable model, unavailable
   FFmpeg, upgrade rollback, and evidence recovery.
4. Freeze the supported matrix, operating runbook, escalation path, monitoring thresholds,
   and rollback authority for the pilot candidate.

### Phase 3: protected intake

Credential resolution, password-protected archive extraction, and Zoom retrieval remain
separate opt-in products. Each requires its own ADR, threat model, secret lifecycle, disabled-
by-default configuration, hostile-input tests, authorization evidence, and accessibility UAT.
Connector delivery must not delay or weaken the local-only trust baseline.

## Controls completed in this hardening increment

- A versioned eight-gate roadmap with owner roles, exit criteria, linked risks/stories,
  blockers, next actions, promotion impact, and evidence hashes.
- A fail-closed validator that rejects production claims while promotion blockers remain.
- Direct runtime dependency CycloneDX inventory and advisory evidence; this does not replace
  the open full-transitive and installer qualification.
- Four real Chromium cases covering mobile, tablet, desktop, light/dark presentation,
  keyboard tab navigation, skip-link focus, named dialogs, overflow, security headers,
  console errors, and unexpected network requests.
- Fixed dark-mode action/status contrast, mobile readiness access, keyboard tab behavior,
  dialog/media/progress semantics, and additional cross-origin response protections.

## Promotion record required

The release governance lead must record candidate revision, package/model/tool hashes,
roadmap version, gate report hash, full test and architecture results, accepted residual risks,
named approvers, rollback artifact, and decision expiry. If a gate later drifts or its evidence
expires, the decision returns to `proceed_with_conditions` automatically.
