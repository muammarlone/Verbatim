# ADR-004: bounded, memory-only manifest preview

- Status: accepted for STS-105/106
- Date: 2026-07-29
- Scope: CSV/XLSX import-plan preview only

## Context

The protected-recording epic needs a way to validate up to 25 recording references before any
credential lookup, archive extraction, network request, or transcription starts. Workbooks are
container formats with active, hidden, external, and parser-exhaustion features. A preview that
persists the upload or returns credential targets would enlarge the sensitive-data boundary before
the later credential and connector stories are qualified.

## Decision

Verbatim accepts UTF-8 CSV and non-macro XLSX through a disabled-by-default loopback mutation
route. The ASGI boundary and parser both enforce a maximum 5 MiB request artifact. The standard
library parser accepts a seven-column schema, at most 25 data rows, and a deliberately narrow XLSX
subset. It rejects formulas/formula-like CSV values, external relationships, macros, embedded or
hidden workbook features, unsafe ZIP entries, non-text cells, path traversal, arbitrary URLs,
plaintext secret fields, and ambiguous source rows with versioned reason codes.

Validated plans live only in a bounded process-memory store for at most 30 minutes. The API preview
returns source metadata plus a provider category; it never returns the `prompt://` label or
`wincred://` target. Audit records contain only plan ID, schema version, row count, and manifest
SHA-256. Preview performs no processing readiness check, secret resolution, extraction, download,
job creation, or source persistence.

The later execute, credential, archive, and Zoom paths remain absent and their feature flags remain
off. Their ADR gates in the approved epic still apply.

## Consequences

- Restart and expiry intentionally invalidate unexecuted plans.
- Strict XLSX files may need to be generated from the approved template rather than arbitrary
  feature-rich spreadsheets.
- The application adds no spreadsheet library or remote dependency.
- The current local upload and folder workflows retain their behavior when manifest intake is off.
- Passing parser tests establishes contract behavior only; it does not qualify archive or Zoom
  processing, Windows deployment, accessibility, or production readiness.
