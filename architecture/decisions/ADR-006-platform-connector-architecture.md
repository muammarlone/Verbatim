# ADR-006 — Platform Connector Architecture: Zoom, Teams, and Password-Protected Intake

**Status:** Proposed — BLOCKED pending threat model, owner assignment, and Phase 1 gate clearance  
**Date:** 2026-07-30  
**Linked stories:** STS-107, STS-108, STS-109, STS-121, STS-122  
**Linked gate:** QG-07 (non-blocking until Phase 1 trust gates pass)  
**Linked risks:** R-14, R-15, R-16  

---

## Context

Verbatim currently accepts recordings dropped into an approved local folder (single-file upload or batch workspace). Corporate users hold large libraries of meeting recordings in:

1. **Zoom Cloud** — retrieved via Zoom REST API with OAuth 2.0 user credentials
2. **Microsoft Teams / OneDrive** — retrieved via Microsoft Graph API with Azure AD delegated credentials
3. **Password-protected archives** — corporate recordings exported as ZIP/7z files with meeting passwords

A CSV manifest intake mechanism already exists (STS-106) with a `secret_ref` column that references named credentials. This ADR defines how platform connectors extend that mechanism without re-architecting the core transcription pipeline.

### Why local-first matters for the connector pitch

Verbatim's differentiator is **local transcription with auditable deletion**: the audio never leaves the endpoint, no cloud transcription API sees the content. Platform connectors extend reach (Zoom/Teams recordings are accessible) while preserving that guarantee: download → local disk → Whisper → delete download. This is the argument for regulated enterprises choosing Verbatim over sending recordings to cloud transcription services.

---

## Decision: Connector isolation model

Each platform connector is:

- A **separate feature flag** (`STS_ZOOM_CONNECTOR_ENABLED`, `STS_TEAMS_CONNECTOR_ENABLED`)  
- A **separate ADR** for its credential lifecycle and threat model  
- **Disabled by default** — the core application ships without connector code in the hot path  
- **Download-only** — connectors write a temporary local copy; the existing service pipeline processes it; the temporary copy is deleted on job completion or failure  

No connector may: persist credentials in plaintext, log access tokens, store recordings outside the approved workspace, or bypass the existing upload-size and duration budgets.

---

## Platform comparison

| Dimension | Zoom | Microsoft Teams | Password-protected ZIP |
|---|---|---|---|
| Auth mechanism | OAuth 2.0 PKCE (user-level), Zoom Marketplace app registration | Microsoft Graph OAuth 2.0, Azure AD app registration, delegated `OnlineMeetings.Read` + `CallRecords.Read.All` | Credential Locker lookup by `secret_ref` name (STS-107) |
| Token lifetime | Access token 1 h, refresh token 90 days | Access token 1 h, refresh token configurable by tenant admin | Password never stored — looked up per-session from OS Credential Locker |
| Recording endpoint | `GET /v2/meetings/{meetingId}/recordings` → `download_url` | `GET /communications/callRecords/{id}` + Graph Files API | Local ZIP path from manifest `file_path` column |
| Password field in manifest | `meeting_password` column in CSV → Credential Locker ref | Not applicable (OAuth token is the credential) | `password_ref` column → Credential Locker ref |
| Corporate risk level | **High** — crosses external SaaS boundary; Zoom must be in approved vendor list | **Medium** — within M365 tenant boundary; lower data-transfer risk | **Low** — fully local; password is the only external secret |
| Pilot priority | Phase 3B (after Teams) | Phase 3A (preferred first connector — stays inside corporate boundary) | Phase 3A concurrent with Teams |
| Scope creep risk | High — Zoom API can access org-wide recordings; scope must be minimum | Medium — Graph scope can be broad; delegated scope limits to user's own meetings | Low — scoped to one archive at a time |

### CSV manifest extension for connector intake

The existing STS-106 manifest schema is extended with connector-specific columns:

```
file_name, platform, meeting_id, secret_ref, notes
recording-2026-07.zoom, zoom, abc123def456, zoom-oauth-token-prod, Q3 review
recording-2026-07.teams, teams, 19:thread-id@thread.v2, teams-graph-token-prod, Planning sync
archive-2026-07.zip, local_archive, archive-2026-07.zip, zip-password-wfm, WFM requirements
```

`secret_ref` values are names in Windows Credential Locker — never the credential itself. The connector resolves the ref at download time and discards the resolved value after use. The manifest parser already enforces a 25-row cap and 5 MiB size limit (STS-106); connector columns are additive and backward-compatible.

---

## Options considered

### Option A — Single unified connector module (rejected)
One module handles Zoom, Teams, and archive extraction. Simpler code; but a vulnerability in one connector's credential handling exposes all connectors. Violates least-privilege.

### Option B — Separate isolated connector modules per platform (recommended)
Each connector is a separate Python module with its own feature flag, ADR, and threat model. A flaw in the Zoom connector cannot affect the Teams connector or archive extractor. Each connector ships independently after its own gate review.

### Option C — External connector service over loopback (deferred)
Connectors run as a separate process with IPC over loopback. Maximum isolation, but adds deployment complexity before Phase 1 gates are even cleared. Reconsider if connector threat models reveal unacceptable risk in Option B.

---

## Recommendation

**Option B** — separate modules per platform, in this sequence:

1. **Phase 3A:** STS-108 (password-protected ZIP) + STS-121 (Teams Graph connector) — both stay inside the corporate trust boundary
2. **Phase 3B:** STS-109 (Zoom OAuth/PKCE) — requires external vendor approval and Zoom Marketplace registration

---

## Pre-implementation requirements (all must be satisfied before any connector code)

For **each** connector:

- [ ] Approved threat model covering: credential storage, token refresh, network boundary, hostile download, cleanup on failure
- [ ] IT-approved vendor entry (Zoom: Marketplace app; Teams: Azure AD app registration with minimum delegated scope)
- [ ] Secret lifecycle defined: provisioning, rotation, revocation, audit trail
- [ ] Hostile-input protocol: malformed download URL, redirect, oversized response, SSRF
- [ ] Connector-specific ADR approved by connector security lead
- [ ] Phase 1 trust gates (QG-01 through QG-06) have accountable owners and accepted plans

---

## Consequences

- Zoom, Teams, and archive connectors remain unimplemented until the above requirements are met
- CSV manifest schema is forward-compatible with connector columns today — no manifest changes needed
- `STS_ZOOM_CONNECTOR_ENABLED`, `STS_TEAMS_CONNECTOR_ENABLED`, `STS_PROTECTED_ARCHIVE_ENABLED` remain `false` by default until each connector's gate passes
- Operators can document Zoom and Teams recording metadata in a manifest now and process them manually; the connector automates the download step only

---

## References

- STS-106: Bounded CSV/XLSX manifest preview (done)
- STS-107: Windows Credential Locker `secret_ref` resolution (not_started)
- STS-108: Password-protected ZIP/7z extraction (not_started)
- STS-109: Zoom OAuth/PKCE download connector (not_started)
- STS-121: Microsoft Teams / Microsoft Graph recording connector (not_started — new, this ADR)
- STS-122: Connector-specific acceptance testing harness (not_started — new, this ADR)
- ADR-004: Bounded manifest preview
- QG-07: Protected archive and Zoom intake gate
