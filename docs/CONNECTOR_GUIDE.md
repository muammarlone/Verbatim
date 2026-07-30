# Verbatim Recording Connector Guide

This guide covers the manifest-based recording intake system — the CSV/XLSX format,
secret reference schemes, validation rules, and the planned connector workflows for
Microsoft Teams and Zoom Cloud recordings.

**Status summary**

| Component | Status | Gate |
|---|---|---|
| CSV/XLSX manifest parser and preview API | Backend contract only; disabled by default | STS-106 |
| `wincred://` secret reference scheme | Planned — not implemented | STS-107 |
| `prompt://` secret reference scheme | Planned — not implemented | STS-107 |
| Password-protected archive extraction | Not available | STS-108 |
| Teams recording connector (Phase 3A) | Not available — planned | STS-121 |
| Zoom recording connector (Phase 3B) | Not available — planned | STS-122 |

Enable `STS_MANIFEST_INTAKE_ENABLED=true` only in an approved contract-test environment.
It does not execute acquisition, transcription, or credential resolution in any state.

---

## CSV manifest format

A manifest is a UTF-8 CSV or XLSX workbook that lists the recordings to be processed
in a single intake run. It must have exactly seven columns in this exact order.

### Column specification

| # | Column | Type | Required | Format / constraint |
|---|---|---|---|---|
| 1 | `schema_version` | String | Yes | Must be exactly `1.0` |
| 2 | `row_id` | String | Yes | `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` — up to 64 chars, starts with alphanumeric |
| 3 | `source_type` | Enum | Yes | `local_archive` or `zoom_recording` |
| 4 | `source_locator` | String | Yes | See per-type rules below |
| 5 | `secret_ref` | String | Conditional | See secret reference schemes below |
| 6 | `display_name` | String | Yes | Human-readable name, up to 512 chars, no control characters |
| 7 | `expected_sha256` | String | No | 64-character lowercase hex SHA-256, or leave blank |

### Hard limits

| Constraint | Value |
|---|---|
| Maximum file size | 5 MiB |
| Maximum rows (excluding header) | 25 |
| Maximum field length | 512 characters |
| Maximum `wincred://` references per manifest | 20 |
| Formula prefix rejection | `=`, `+`, `-`, `@` are forbidden in any cell |
| Control characters | `\x00–\x1f` (except `\t`, `\n`, `\r`) are forbidden |

### Exact header row

The first row must be exactly:

```
schema_version,row_id,source_type,source_locator,secret_ref,display_name,expected_sha256
```

No BOM, no extra columns, no reordering.

---

## Source types

### `local_archive` — password-protected local recording

Use for recordings stored on the local machine in a password-protected ZIP or 7z archive.

**`source_locator` format**

```
<folder_segment>/<archive_name>/<entry_name>
```

Each path segment must match `[A-Za-z0-9][A-Za-z0-9._ -]{0,99}`. Windows reserved names
(`CON`, `NUL`, `COM1`, etc.) and path traversal sequences are rejected.

**`secret_ref` requirement**

One of:

| Scheme | Format | Resolves via |
|---|---|---|
| `prompt://` | `prompt://<label>` | Operator prompted at intake time (planned — STS-107) |
| `wincred://` | `wincred://<credential-target>` | Windows Credential Locker (planned — STS-107) |

Example:

```
1.0,row-001,local_archive,Q2-Reviews/quarterly-review.zip/recording.mp4,wincred://Verbatim/Q2Password,Q2 Board Review 2026,
```

---

### `zoom_recording` — Zoom Cloud recording

Use for recordings hosted in Zoom Cloud. The connector retrieves via Zoom API using
user-delegated OAuth (PKCE), then deletes the temporary local copy after transcription.

**`source_locator` format**

```
<recording_id>:<file_id>
```

Both segments must match `[A-Za-z0-9_-]{8,128}`. Obtain these IDs from the Zoom API
or from the Zoom meeting dashboard under **Cloud Recordings**.

**`secret_ref` requirement**

Leave **blank**. Zoom rows authenticate via user OAuth; there is no password stored in
the manifest. Providing a non-empty `secret_ref` on a Zoom row is a hard validation error.

Example:

```
1.0,row-002,zoom_recording,AbCdEfGh12345678:XyZ9876543abcdef,, Q2 All-Hands Recording,a3b4c5d6...
```

---

## Secret reference schemes (planned — STS-107)

Secret references point to a credential that Verbatim resolves at runtime, without
writing the actual value to the manifest, any log, or any audit event.

### `prompt://` — operator-prompted at intake

```
prompt://<label>
```

`<label>` is a human-readable hint shown to the operator when they are prompted to
enter the password interactively. The value is held in memory only for the duration
of the extraction and is not persisted.

**Rules:**
- `<label>` must match `[A-Za-z0-9][A-Za-z0-9._ -]{0,63}`
- A manifest may have multiple `prompt://` references; the operator is prompted once per distinct label
- The entered value is never written to disk, logged, or included in audit events

### `wincred://` — Windows Credential Locker

```
wincred://<credential-target>
```

`<credential-target>` is the target name of a Windows Generic credential stored by the
operator in the Windows Credential Manager. Verbatim reads it via the Windows Credential
API at intake time.

**Rules:**
- `<credential-target>` must match `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}`
- A manifest may reference up to 20 distinct `wincred://` targets
- The operator must pre-load the credential in Windows Credential Manager before submitting the manifest
- The resolved secret is held in memory only, never written to disk or audit events

**Pre-loading a credential in Windows Credential Manager:**

1. Open **Credential Manager** from Windows Settings or `Control Panel`.
2. Select **Windows Credentials** → **Add a generic credential**.
3. Set **Internet or network address** to match the `wincred://` target (e.g., `Verbatim/Q2Password`).
4. Set **User name** to any identifier (e.g., `verbatim-operator`).
5. Set **Password** to the archive password.
6. Click **OK**.

The credential stays in the locker until the operator removes it. Remove it after the
intake run completes and the archive is no longer needed.

---

## XLSX workbook requirements

XLSX files follow the same column order and validation rules as CSV.

| Requirement | Detail |
|---|---|
| Active worksheet | First worksheet only is read |
| Row limit | 25 data rows (row 1 must be the header) |
| Forbidden features | Formulas, macros (VBA), external links, pivot tables, drawings, hyperlinks, hidden rows, zero-width columns, merged cells, data validation dropdowns |
| Compression safety | Expansion ratio must be below 200×; maximum expanded size 20 MiB |
| Column boundary | Data outside column G (the seventh column) is rejected |

---

## Validation error codes

| Code | Meaning | Fix |
|---|---|---|
| `MANIFEST_COLUMNS_INVALID` | Header row or data row does not have exactly 7 columns in the required order | Verify the header matches the exact column specification |
| `MANIFEST_SCHEMA_VERSION_INVALID` | `schema_version` is not `1.0` | Set `schema_version` to `1.0` in every row |
| `MANIFEST_ROW_ID_INVALID` | `row_id` does not match the alphanumeric pattern | Remove spaces and special characters; start with a letter or digit |
| `MANIFEST_SOURCE_TYPE_INVALID` | `source_type` is not `local_archive` or `zoom_recording` | Use exactly `local_archive` or `zoom_recording` |
| `MANIFEST_SECRET_REF_INVALID` | `secret_ref` format is wrong, or a Zoom row has a non-empty ref | Use `prompt://` or `wincred://` for archives; leave blank for Zoom rows |
| `MANIFEST_LOCATOR_INVALID` | `source_locator` contains path traversal, reserved names, or wrong Zoom format | Correct the path segments or Zoom `recording_id:file_id` format |
| `MANIFEST_DUPLICATE_ROW_ID` | Two rows share the same `row_id` | Make every `row_id` unique within the manifest |
| `MANIFEST_TOO_LARGE` | File exceeds 5 MiB | Split into smaller manifests |
| `MANIFEST_TOO_MANY_ROWS` | More than 25 data rows | Split into smaller manifests |
| `MANIFEST_FORMULA_INJECTION` | A cell starts with `=`, `+`, `-`, or `@` | Remove formula prefixes from all cells |
| `MANIFEST_CONTROL_CHARACTERS` | A field contains non-printable control characters | Clean the field values |
| `MANIFEST_SHA256_INVALID` | `expected_sha256` is not a 64-character lowercase hex string | Correct or blank the SHA-256 field |
| `MANIFEST_XLSX_FEATURE_FORBIDDEN` | Workbook contains forbidden features (macros, links, drawings) | Save a clean XLSX with only plain cell values |
| `MANIFEST_WINCRED_CAP_EXCEEDED` | More than 20 `wincred://` references | Split the manifest or reuse credential targets |

---

## Planned connector workflows

### Teams recording connector — Phase 3A (not yet implemented)

**Pre-conditions before this connector can be used:**
- ADR-006 Phase 3A approved by security lead
- Azure AD application registered with minimum scope (`OnlineMeetings.Read`)
- IT approval of the Azure AD app
- `STS_TEAMS_CONNECTOR_ENABLED=true` set by IT (never set by the operator)
- All Phase 3A pre-implementation conditions met (see `architecture/pre-implementation/STS-121-teams-connector.md`)

**Planned workflow when available:**

1. Operator creates manifest with `zoom_recording`-equivalent Teams rows (format TBD pending Phase 3A ADR).
2. Operator submits the manifest via the Verbatim UI.
3. Verbatim validates the manifest (CSV format + locator bounds).
4. Verbatim initiates Microsoft Graph OAuth flow — operator approves in browser.
5. Verbatim downloads the recording to the local approved workspace (`STS_DATA_DIR`).
6. Verbatim transcribes locally using the approved Whisper model.
7. Verbatim deletes the temporary local copy immediately after transcription.
8. Transcript and audit event are written; the OAuth token expires per the configured lifetime.

**Audio never leaves the corporate tenant boundary (after Phase 3A is implemented).**

---

### Zoom Cloud recording connector — Phase 3B (not yet implemented)

**Pre-conditions before this connector can be used:**
- STS-107 (Credential Locker) complete
- STS-109 (Zoom OAuth/PKCE) complete
- ADR-006 Phase 3B approved by security lead
- Zoom Marketplace app approved by IT
- `STS_ZOOM_CONNECTOR_ENABLED=true` set by IT (never set by the operator)
- All Phase 3B pre-implementation conditions met (see `architecture/pre-implementation/STS-122-zoom-manifest-connector.md`)

**Planned workflow when available:**

1. Operator creates manifest with `zoom_recording` rows (column 3 = `zoom_recording`).
2. For password-protected recordings, the meeting password is stored in Windows Credential Manager; the manifest uses `wincred://` (not needed for Zoom rows — Zoom uses OAuth).
3. Operator submits the manifest via the Verbatim UI.
4. Verbatim validates the manifest (7-column CSV, Zoom locator format, blank `secret_ref`).
5. Verbatim initiates Zoom OAuth PKCE flow — operator approves in browser.
6. Verbatim retrieves the recording from Zoom API using the bounded `recording_id:file_id` locator.
7. Verbatim validates the download against `expected_sha256` (if provided).
8. Verbatim transcribes locally using the approved Whisper model.
9. Verbatim deletes the temporary local copy immediately after transcription.
10. Transcript and audit event are written; the OAuth token expires per the configured lifetime.

**Audio never leaves the local endpoint after download.**

---

## Complete manifest examples

### Local archive manifest

```csv
schema_version,row_id,source_type,source_locator,secret_ref,display_name,expected_sha256
1.0,q2-board-001,local_archive,Q2-Board/recordings.zip/board-session-1.mp4,wincred://Verbatim/Q2BoardPassword,Q2 Board Session 1,
1.0,q2-board-002,local_archive,Q2-Board/recordings.zip/board-session-2.mp4,wincred://Verbatim/Q2BoardPassword,Q2 Board Session 2,
1.0,legal-hold-01,local_archive,Legal/hold-2026.zip/deposition-a.mp4,prompt://Legal Hold Password,Deposition A — 2026-07-15,a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4
```

### Zoom manifest

```csv
schema_version,row_id,source_type,source_locator,secret_ref,display_name,expected_sha256
1.0,zoom-qtr-001,zoom_recording,AbCdEfGh12345678XyZ9:MnOpQrSt56789012Ab,,Q2 All-Hands — 2026-07-01,
1.0,zoom-qtr-002,zoom_recording,BcDeFgHi23456789YzA0:NoPqRsTu67890123Bc,,Q2 Town Hall — 2026-07-08,
```

---

## Security rules that cannot be waived

1. **Never write actual passwords, tokens, or secrets into the manifest CSV.** Use `secret_ref` exclusively.
2. **Never enable connector flags in CI, Codespaces, or development environments.** Only IT may set `STS_ZOOM_CONNECTOR_ENABLED` or `STS_TEAMS_CONNECTOR_ENABLED`.
3. **Remove Credential Manager entries after the intake run completes.** Lingering credentials increase the blast radius of a compromised endpoint.
4. **Do not share manifests outside the approved enclave.** Even without secrets, manifest `source_locator` values reveal internal file structure and recording schedules.
5. **Verify `expected_sha256` for sensitive recordings.** This ensures the downloaded file has not been tampered with in transit.
