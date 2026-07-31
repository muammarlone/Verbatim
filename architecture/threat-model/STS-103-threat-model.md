# Threat Model — STS-103: OS Authentication and Credential Storage

**Version:** 1.0 — 2026-07-31
**Author:** Virtual AI — Information Security Officer (AI)
**Reviewed by:** Principal Security and Privacy Architect (AI)
**Status:** Draft — pending QG-03 managed-endpoint review
**ADR:** ADR-008-os-auth.md

---

## Scope

Authentication and credential storage for Verbatim STS on a managed corporate Windows endpoint.
Covers: user session identity, Windows Credential Locker operations, in-memory credential values,
and the `STS_OS_AUTH_ENABLED` configuration boundary.

Out of scope: network authentication, OAuth flows (STS-109), manifest secret_ref resolution
(STS-107), and data-at-rest encryption of transcripts (ADR-007).

---

## Assets

| Asset | Sensitivity | Location |
|-------|-------------|----------|
| User session identity | HIGH | Windows session token (OS-managed) |
| Credential value in memory | CRITICAL | Between `CredReadW` call and use — transient |
| Credential blob in Locker | HIGH | OS Credential Locker (`CRED_TYPE_GENERIC`, per-user) |
| `STS_OS_AUTH_ENABLED` flag | MEDIUM | Environment variable / IT deployment config |
| Dev stub enablement state | MEDIUM | Environment variable |

---

## Threat actors

| Actor | Capability | Likelihood |
|-------|-----------|-----------|
| Local process (same user) | Read process memory, OS Credential Locker | HIGH in shared endpoint |
| Privileged local process (admin) | Read any user's Locker, memory dump | MEDIUM |
| Config file reader | Read `.env`, startup scripts, deployment configs | HIGH if not governed |
| Network attacker | No direct path — app is localhost-only | LOW |

---

## STRIDE analysis

### Spoofing

| Threat | Scenario | Control | Residual risk |
|--------|----------|---------|--------------|
| S-01 Dev stub active in prod | IT deploys without setting `STS_OS_AUTH_ENABLED=true` | IT deployment checklist (operator-checklist.md) requires the flag | IT oversight gap — mitigated by checklist; not automated |
| S-02 Non-Windows enablement | Dev sets `STS_OS_AUTH_ENABLED=true` on macOS | Factory raises `RuntimeError` immediately; tests cover this | None — hard block |
| S-03 Session impersonation | Attacker runs app under victim's Windows session | Windows session isolation is OS control | Out of Verbatim's scope — OS responsibility |

### Tampering

| Threat | Scenario | Control | Residual risk |
|--------|----------|---------|--------------|
| T-01 Credential value corrupted | Attacker overwrites Locker entry | `CRED_TYPE_GENERIC` entries writable by owner only | Owner-privilege attacker can overwrite; accepted |
| T-02 `STS_OS_AUTH_ENABLED` toggled | Attacker sets flag to `false` to bypass auth | Flag requires process restart; IT manages env config | Config management scope — not application scope |

### Repudiation

| Threat | Scenario | Control | Gap |
|--------|----------|---------|-----|
| R-01 No record of `get_credential` calls | Attacker reads credential; no audit trail | — | **OPEN** — audit logging of Locker access not implemented. ADR-007 AuditStore is content-free and cannot record credential values. Windows Event Log entry may be required by IT policy. |

### Information Disclosure

| Threat | Scenario | Control | Residual risk |
|--------|----------|---------|--------------|
| I-01 Credential in application log | `store_credential(key, value)` logs `value` | Value never referenced after `CredWriteW` call; not passed to any log function | None — by design |
| I-02 Credential in audit store | AuditStore records credential operation | AuditStore is content-free (SHA-256 hashes only); credential operations are not audited | None — by design |
| I-03 Credential in memory dump | Attacker dumps process memory between `CredReadW` and use | OS-level memory protection on managed endpoint (VBS, Credential Guard) | Residual — accept; managed endpoint mitigates |
| I-04 Credential in environment | Attacker reads `STS_OS_AUTH_ENABLED` or related env vars | Flag is boolean only; no credential value in env | None — flag carries no secret |
| I-05 Credential in backup | Windows Credential Locker included in roaming profile backup | `CRED_PERSIST_LOCAL_MACHINE` (2) — not roamed | IT must verify backup exclusion on managed endpoint |

### Denial of Service

| Threat | Scenario | Control | Residual risk |
|--------|----------|---------|--------------|
| D-01 `CredDeleteW` removes credential | Operator deletes a required credential; app fails to retrieve it | `delete_credential` returns silently if key not found; app must handle `None` from `get_credential` | Caller must handle `None` — documented in interface |
| D-02 Locker API unavailable | `advapi32.dll` not present | Only reachable when `STS_OS_AUTH_ENABLED=true` on Windows — `advapi32.dll` is always present on Windows | None |

### Elevation of Privilege

| Threat | Scenario | Control | Residual risk |
|--------|----------|---------|--------------|
| E-01 `advapi32` API misuse | Exploit via malformed target name | `CRED_TYPE_GENERIC` only; target name is `"Verbatim/" + key` with no user-controlled path component | Low — standard API usage |
| E-02 Credential enables further access | Retrieved credential used to access additional systems | Credential use is caller responsibility; Verbatim does not escalate beyond its own API calls | Out of scope — credential consumer is responsible |

---

## Controls implemented

| Control | Implementation |
|---------|---------------|
| Default-off | `STS_OS_AUTH_ENABLED=false` default; `DevAuthStub` is no-op |
| Platform guard | `get_auth_provider()` raises `RuntimeError` on non-Windows if enabled |
| No plaintext log | `store_credential` never logs or stores `value` after `CredWriteW` |
| Memory cleanup | `CredFree` called in `finally` in `get_credential` |
| Local persistence | `CRED_PERSIST_LOCAL_MACHINE` — not roamed |
| Type restriction | `CRED_TYPE_GENERIC` only — no system or domain credentials |
| Target prefix | `Verbatim/` prefix isolates from other apps' Locker entries |

---

## Open items for QG-03

| Item | Owner | Gate |
|------|-------|------|
| Audit logging of credential access events | Information Security Officer (human) | QG-03 |
| Key rotation procedure documented | Information Security Officer (human) | QG-03 |
| Backup exclusion verified on managed endpoint | IT Systems Engineer (human) | QG-03 |
| `app.py` enforcement wiring | Principal Architect (AI) | Post QG-03 |
| Pen test of auth surface | Independent security function (human) | QG-03/QG-04 |
| Credential Guard / VBS verification | IT Systems Engineer (human) | QG-03 |

---

## Residual risks accepted

| Risk | Justification |
|------|--------------|
| In-memory credential value readable by privileged process | OS-level Credential Guard on managed endpoint mitigates; accepted for corporate pilot scope |
| No audit log of Locker reads | Content-free audit store cannot record values; Windows Event Log by IT policy is the compensating control |
| IT configuration gap (stub in prod) | Mitigated by deployment checklist; not automated — accepted for course-project context |
