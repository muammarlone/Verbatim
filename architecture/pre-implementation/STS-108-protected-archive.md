# STS-108 Pre-Implementation Requirements: Password-Protected Archive Adapter

**Status**: BLOCKED — not authorized for implementation until all conditions below are met.
**Story**: As an authorized operator, I can extract a bounded password-protected ZIP/7z recording
through a qualified adapter.

## Blocking conditions (all must be satisfied before implementation begins)

1. **Security spike required**: A time-boxed security spike must evaluate at least two adapter
   libraries (e.g., zipfile + py7zr) for traversal, symlink-follow, and bomb resistance
   before choosing an approach. The spike result must be reviewed by the security lead.

2. **Adapter ADR required**: An approved ADR must document the chosen library, its known
   vulnerabilities, version pin, mitigation for decompression bombs, path-traversal defenses,
   and post-extraction cleanup contract.

3. **Threat model required**: A written threat model covering:
   - Path traversal (zip slip) via crafted archive entries
   - Symlink-follow leading to out-of-boundary file reads/writes
   - Decompression bomb (e.g., 42.zip) exhausting disk or memory
   - Polyglot archives (valid zip + malicious payload)
   - Password oracle attacks via timing side-channels
   - Temporary file residue after extraction failure

4. **Hostile corpus required**: Test cases for each threat class above (traversal entries,
   symlinks, decompression bombs, polyglots) must be designed and reviewed before implementation.

5. **Owner required**: A named security lead must accept ownership of the adapter security review.

## Acceptance evidence (when blocked conditions are cleared)

- Security spike decision record with library comparison
- Approved adapter ADR
- Traversal/symlink/bomb corpus passing (negative controls fail-closed)
- Cleanup and timeout tests
- Decompression bomb test (archive bomb detected and rejected within resource budget)

## Linked

- Linked stories: STS-106 (manifest preview), STS-107 (credential locker)
- Linked risk: R-14, R-16
- Linked gate: QG-03 (penetration testing)

## Claim boundary

ASSUMPTION: This feature is not implemented, not tested for production use, and not
available to operators. The production claim is `STS_PROTECTED_ARCHIVE_ENABLED=false` by default.
No bypass of this requirement stub is authorized.
