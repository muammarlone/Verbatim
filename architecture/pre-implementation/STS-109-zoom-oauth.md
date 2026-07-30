# STS-109 Pre-Implementation Requirements: Zoom Cloud Recording OAuth/PKCE Connector

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized Zoom user, I can retrieve an authorized recording through user OAuth
with PKCE and bounded download controls.

## Blocking conditions (all must be satisfied before implementation begins)

1. **ADR-006 approved**: The platform connector architecture ADR (ADR-006) exists but requires
   security lead sign-off for the Zoom Phase 3B scope specifically, including the PKCE flow,
   scope allowlist, redirect URI pinning, and token storage contract.

2. **Zoom threat model required**: A written threat model for this connector covering:
   - Redirect URI hijacking (open redirect → OAuth token theft)
   - Scope creep (user grants more than minimum required scope)
   - SSRF via Zoom API redirect (attacker-controlled recording URL)
   - Oversized recording download exhausting disk or network budget
   - Token exfiltration via log injection
   - Meeting password resolution (must route through STS-107 credential locker)

3. **Zoom Marketplace app approval**: The Zoom OAuth application must be reviewed and approved
   by IT and the security lead before any OAuth flow is implemented. App ID, allowed scopes,
   and redirect URIs must be documented.

4. **STS-107 must be complete**: Zoom meeting passwords resolved via `secret_ref` require
   the Windows Credential Locker provider (STS-107) to exist before Zoom connector can proceed.

5. **Owner required**: A named security lead must accept ownership of the Zoom connector
   threat model and OAuth application configuration.

6. **Hostile-redirect corpus required**: Test cases for open redirect, oversized response,
   SSRF via crafted meeting URL, and scope validation must be designed before implementation.

## Acceptance evidence (when blocked conditions are cleared)

- Scope/host allowlist tests (reject out-of-allowlist recording URLs)
- OAuth expiry/revocation tests (token refresh and graceful revocation)
- Rate-limit and redirect validation tests
- Oversized-response rejection test (bounded download cap)
- Synthetic connector fixture end-to-end (no real Zoom credentials in CI)
- `STS_ZOOM_CONNECTOR_ENABLED` defaults false in all environments

## Linked

- Linked stories: STS-107 (credential locker, prerequisite), STS-122 (Zoom manifest integration)
- Linked risk: R-14, R-15
- Linked ADR: ADR-006 (connector isolation model)
- Linked gate: QG-03 (penetration testing), QG-01 (domain eval lead)

## Claim boundary

ASSUMPTION: This feature is not implemented, not tested for production use, and not
available to operators. The production claim is `STS_ZOOM_CONNECTOR_ENABLED=false` by default.
No bypass of this requirement stub is authorized. No Zoom credentials may be introduced
into any Codespaces, CI, or development environment.
