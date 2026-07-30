# Claude Code Handoff: Secure Protected-Recording Intake

Prepared July 29, 2026 for [GitHub issue #1](https://github.com/muammarlone/Verbatim/issues/1).

## Mission

Implement the smallest demonstrable, governed vertical slice of the approved epic in
`governance/EPIC_SECURE_PROTECTED_RECORDING_INTAKE.md`. Preserve the existing local MP4,
folder-batch, transcription, analysis, export, retention, and deletion behavior.

The first delivery is **STS-105 plus STS-106 only**: synchronize architecture/evaluation
contracts, then implement a strict CSV/XLSX manifest parser and sanitized preview API. Do not
implement archive extraction, secret providers, Zoom OAuth, packaging, Docker, Codespaces, or
UI polish in that first delivery.

## Repository state

- Repository: `muammarlone/Verbatim`
- Target branch: `main`
- Planning baseline before this handoff: `d168f813af9955940e7c1e3237d8231f9893951b`
- Canonical scope: `governance/EPIC_SECURE_PROTECTED_RECORDING_INTAKE.md`
- Traceability: `governance/BACKLOG.md`, `governance/RISK_REGISTER.md`, and issue #1
- Existing release evidence: 19 architecture gates, 45 tests, and measured 82% branch coverage
  at the planning baseline; remeasure rather than repeating these figures as current after edits.

## Non-negotiable boundaries

1. Keep the current maximum of 25 manifest rows and the existing batch byte/duration budgets.
2. Accept CSV and non-macro `.xlsx` only. Reject `.xls`, `.xlsm`, external links, formulas,
   embedded objects, and unrecognized columns before resolving a secret or opening a network
   connection.
3. Treat every workbook cell, URL, archive entry, connector response, and tool output as
   untrusted data.
4. A manifest may contain `secret_ref`; it may never contain or return a password or OAuth
   token. Sanitized preview responses and logs must not expose secret values.
5. Preview performs no secret resolution, download, extraction, transcription, or durable source
   import. Its plan record expires after the bounded lifetime defined in the epic.
6. Use deterministic schemas, stable reason codes, bounded retries/timeouts, atomic writes,
   idempotent state transitions, and fail-closed behavior.
7. Do not put corporate recordings, personal data, real Zoom credentials, or production secrets
   in source control, fixtures, screenshots, Codespaces, logs, or evaluation evidence.
8. Preserve mutation-token and loopback-only controls. Networking remains disabled unless the
   separate Zoom feature is explicitly enabled and qualified in STS-109.
9. Update the backlog, risk register, L1-L3 architecture, evaluation catalog/report, and evidence
   index in the same change whenever behavior or scope changes materially.
10. Do not claim compliance, transcript accuracy, security, performance, or deployment readiness
    beyond reproducible evidence.

## Required first-delivery contracts

Before writing parser code, pin a versioned import-manifest schema and reason-code catalog. Define
at minimum:

- UTF-8/UTF-8-BOM CSV decoding, delimiter/newline behavior, header normalization, empty-row
  handling, duplicate-header policy, cell/row/file byte limits, and rejection behavior.
- XLSX identification by validated package structure rather than extension alone; one allowed
  visible worksheet; no formulas, macros, external relationships, hidden data, embedded objects,
  or malformed shared strings.
- Exact source discriminators and required fields for local MP4, protected archive, and Zoom
  rows; reject mixed or ambiguous row types.
- Sanitized preview request, response, error envelope, plan expiry, immutable manifest hash,
  authorization, replay/idempotency, and concurrent-capacity behavior.
- Stable terminal reason codes usable by the later UI and evaluation suite.

Use synthetic fixtures only. Include equivalent valid CSV/XLSX plans and negative fixtures for
wrong content type, renamed formats, formulas, external relationships, hidden sheets, oversized
cells/files, duplicate fields, unknown columns, ambiguous source types, traversal-like paths,
invalid URLs, plaintext secret-like columns, and more than 25 rows.

## Decision gates for later children

Stop and record an ADR or request owner input instead of guessing when a later story reaches any
of these gates:

- **STS-107:** choose the Windows Credential Locker library and specify credential ownership,
  replacement, revocation, deletion, failure, and the 20-distinct-reference limit.
- **STS-108:** qualify the ZIP/7z adapter, including how it receives passphrases without command
  arguments/environment variables; pin entry-count, expanded-byte, compression-ratio, recursion,
  time, and cleanup budgets.
- **STS-109:** pin the official Zoom endpoint version, minimum user OAuth PKCE scopes, tenant
  policy, allowed hosts/redirects, recording-file selection, token lifecycle, request budgets,
  and audit semantics. Do not use scraping or server-to-server account access.
- **STS-110:** IT chooses MSIX or WiX/MSI after an Intune and Configuration Manager spike and
  supplies signing identity, certificate lifecycle, supported Windows versions, installation
  context, repair/upgrade/uninstall rules, and rollback evidence.
- **STS-111/112:** containers and Codespaces remain synthetic developer/test paths, non-root,
  loopback/private-port only, with pinned dependencies and no production vault/data access.
- **STS-113:** product/accessibility owners pin supported browser, keyboard, screen-reader,
  contrast, error-recovery, and pass thresholds before the UI is called pilot-ready.

## Execution order

1. STS-105 — establish versioned contracts, ADRs, threat/evaluation updates, and exact flags.
2. STS-106 — strict manifest parser plus sanitized preview API and hostile-fixture tests.
3. STS-107 — prompt and Windows credential providers.
4. STS-108 and STS-109 — archive and Zoom connectors after their separate gates.
5. STS-110, STS-111, and STS-112 — Windows packaging and synthetic qualification environments.
6. STS-113 — accessible UI/UX fast follow after backend row states stabilize.
7. STS-114 — cross-environment release UAT and conditional pilot decision.

Each child should be independently reviewable and keep unrelated future flags off.

## Verification commands

Run from the repository root on the approved Python 3.11+ environment:

```powershell
python scripts\validate_architecture.py
python -m pytest
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
git diff --check
```

For STS-106, also run the versioned hostile-manifest evaluation and persist its machine-readable
report under the existing evidence conventions. Do not lower an existing threshold to make a
failure pass. If a critical privacy, authorization, deletion, schema, budget, provenance, or
architecture gate fails, stop and narrow the change.

## Expected Claude Code response

Start by reporting the files and contracts inspected, the smallest STS-105/106 increment proposed,
and any conflicting evidence. Then implement and test that bounded increment. End with the exact
changed files, commands/results, residual risks, disabled flags, and decisions still requiring an
owner. Do not merge or push unless the user explicitly authorizes it.

## Quality status

The planning specification passed the repository's public redaction gate with zero findings and
the independent implementation-readiness review at 7/10. The review's unresolved details are
captured above as first-delivery contracts or explicit later decision gates; they are not implicit
implementation authority.
