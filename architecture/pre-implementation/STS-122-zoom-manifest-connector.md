# STS-122 Pre-Implementation Requirements: Zoom Cloud Recording Manifest Connector

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized operator, I can include Zoom Cloud recordings in a CSV manifest
(with meeting_password secret_ref and OAuth token) so that Zoom recordings are retrieved
via Zoom API, transcribed locally, and the temporary copy deleted.

## Blocking conditions (all must be satisfied before implementation below are met)

1. **STS-107 must be complete**: Zoom meeting passwords resolved via `secret_ref` require
   the Windows Credential Locker provider (STS-107). No Zoom password handling is authorized
   before STS-107 is complete and reviewed.

2. **STS-109 must be complete**: The Zoom Cloud OAuth/PKCE connector (STS-109) must exist
   and be reviewed before the manifest integration (STS-122) can be designed. The manifest
   integration is a consumer of the STS-109 connector, not a replacement for it.

3. **ADR-006 Zoom Phase 3B approved**: ADR-006 defines connector isolation but the Phase 3B
   scope (Zoom Marketplace app, PKCE flow, manifest `meeting_password` integration, download
   contract) requires explicit security lead sign-off.

4. **Zoom Marketplace app approved by IT**: The Zoom OAuth application must be reviewed and
   approved by IT before any manifest connector code is written. App credentials (client_id,
   client_secret) must never appear in code, configuration files, environment variables in CI,
   or Codespaces environments.

5. **Threat model required**: The manifest connector threat model must cover, and hostile-redirect corpus must demonstrate defense against:
   - Open redirect via crafted recording URL in the manifest
   - Oversized recording exceeding download budget
   - SSRF via Zoom API redirect to internal host
   - Meeting password brute-force via manifest replay

6. **Owner required**: A named security lead must accept ownership of the Zoom connector and
   Marketplace app configuration.

## Acceptance evidence (when blocked conditions are cleared)

- STS-107 (Credential Locker) complete and reviewed
- STS-109 (Zoom OAuth/PKCE) complete and reviewed
- ADR-006 Phase 3B security lead sign-off
- Zoom Marketplace app reviewed and approved by IT
- Hostile-redirect, oversized-response, SSRF tests passing
- `STS_ZOOM_CONNECTOR_ENABLED=false` default in all environments
- No Zoom credentials in any CI, Codespaces, or dev environment

## Linked

- Linked stories: STS-107 (Credential Locker), STS-109 (Zoom OAuth, both prerequisites)
- Linked risk: R-14, R-15
- Linked ADR: ADR-006 (connector isolation model)
- Linked gate: QG-03 (penetration testing)

## Claim boundary

ASSUMPTION: The Zoom manifest connector is not implemented. The `STS_ZOOM_CONNECTOR_ENABLED`
flag is false in all environments. No Zoom API calls, meeting passwords, OAuth tokens,
or recording downloads are processed by this application. This stub records preconditions
only; no partial implementation is authorized before conditions 1–6 are met.
No Zoom credentials (client_id, client_secret, meeting_password, OAuth token) may be
introduced into any development or CI environment at any point before conditions 1–6 are met.
