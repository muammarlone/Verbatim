# STS-121 Pre-Implementation Requirements: Microsoft Teams Recording Connector

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized operator, I can include Microsoft Teams meeting recordings in a
CSV manifest (with OAuth token secret_ref) so that Teams recordings are downloaded to the
local workspace, transcribed locally, and the temporary copy deleted.

## Blocking conditions (all must be satisfied before implementation begins)

1. **ADR-006 Teams Phase 3A approved**: ADR-006 defines the connector isolation model but
   the Phase 3A implementation scope (Azure AD app registration, minimum delegated scope,
   token lifecycle, download-then-delete contract) requires explicit security lead sign-off
   before any code is written.

2. **Azure AD application approved by IT**: The Azure AD application for Teams connector must:
   - Be registered with minimum delegated scope (OnlineMeetings.Read only)
   - Have redirect URIs pinned to localhost only
   - Have app ID, tenant, and scope documented in a configuration file (not hardcoded)
   - Be reviewed and approved by IT before any OAuth code is written

3. **Token lifecycle document required**: A document specifying:
   - Where the OAuth token is stored (must route through STS-107 Credential Locker)
   - Token expiry and refresh behavior
   - Token revocation procedure
   - What is logged about token operations (no plaintext tokens in audit events)

4. **STS-107 must be complete**: Token `secret_ref` resolution requires the Windows Credential
   Locker provider (STS-107) before the Teams connector can proceed.

5. **Threat model required**: A written threat model covering:
   - Hostile-download: attacker-controlled meeting URL redirects to SSRF target
   - Oversized recording exhausting disk or network budget
   - Token exfiltration via log injection
   - Download-then-delete race: temporary file persists on failure
   - Scope creep: user grants more than OnlineMeetings.Read

6. **Owner required**: A named security lead must accept ownership of the Azure AD app
   configuration and token lifecycle policy.

## Acceptance evidence (when blocked conditions are cleared)

- ADR-006 Phase 3A security lead sign-off
- Azure AD app reviewed and approved by IT
- Token lifecycle document approved
- Hostile-download, redirect, SSRF tests passing (negative controls fail-closed)
- Download-then-delete pipeline audited (temporary copy confirmed deleted)
- `STS_TEAMS_CONNECTOR_ENABLED=false` default in all environments

## Linked

- Linked stories: STS-107 (Credential Locker, prerequisite), STS-122 (Zoom connector)
- Linked risk: R-14, R-15
- Linked ADR: ADR-006 (connector isolation model)
- Linked gate: QG-03 (penetration testing)

## Claim boundary

ASSUMPTION: The Teams connector is not implemented. The `STS_TEAMS_CONNECTOR_ENABLED`
flag is false in all environments. No Azure AD tokens, tenant IDs, or meeting recording
downloads are processed by this application. This stub records preconditions only;
no partial implementation is authorized before conditions 1–6 are met.
