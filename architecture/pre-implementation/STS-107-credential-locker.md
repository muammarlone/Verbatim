# STS-107 Pre-Implementation Requirements: Windows Credential Locker Secret Resolution

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized operator, I can resolve manifest `secret_ref` values through
prompt or Windows Credential Locker without logging or persisting plaintext secrets.

## Blocking conditions (all must be satisfied before implementation begins)

1. **ADR required**: A dedicated ADR for secret lifecycle (storage, rotation, revocation, audit)
   must be reviewed and approved by the security lead. ADR-004 covers architecture boundaries
   but not the credential storage contract itself.

2. **Threat model required**: A written threat model for this feature must exist, covering:
   - Credential theft via memory scraping
   - Privilege escalation via Credential Locker access
   - Logging of plaintext secrets in audit events
   - 20-reference cap bypass via forged manifests
   - Recovery and revocation procedures

3. **Owner required**: A named security lead must accept ownership of the secret lifecycle policy
   before any credential-handling code is written.

4. **Hostile-input protocol required**: A document specifying what happens for each of:
   malformed `secret_ref` values, empty credentials, over-long credentials, credentials
   with injection characters, and expired/revoked credentials.

5. **Redacted audit test required**: Proof that no plaintext secret appears in audit events
   must be designed and reviewed before implementation, not after.

## Acceptance evidence (when blocked conditions are cleared)

- Provider contract tests (prompt provider, Credential Locker provider)
- Redacted audit event tests (no plaintext secret in any log/event)
- Lifecycle and revocation tests (write, read, update, delete, revoke)
- 20-reference cap enforcement test
- Hostile-input corpus test (malformed, empty, over-long, injection)

## Linked

- Linked stories: STS-106 (manifest preview), STS-108 (protected archive), STS-109 (Zoom)
- Linked risk: R-14
- Linked gate: QG-03 (penetration testing), QG-01 (domain eval lead approval)
- Linked architecture: ADR-004, architecture/decisions/ADR-005-windows-installer-packaging.md

## Claim boundary

ASSUMPTION: This feature is not implemented, not tested for production use, and not
available to operators. The production claim is `STS_MANIFEST_INTAKE_ENABLED=false` by default.
No bypass of this requirement stub is authorized.
