# ADR-008: OS-Backed Authentication and Credential Storage

**Status:** Accepted — 2026-07-31
**Story:** STS-103
**Gate:** QG-03 (managed-endpoint verification required before enforcement wiring)
**Owner:** Principal Security and Privacy Architect

---

## Context

Verbatim STS runs on a managed corporate Windows endpoint. Multiple authorized users may share
the endpoint. The application must not store credentials (API keys, passwords, secret references)
in plaintext configuration files, environment variables that appear in shell history, or the
application's own data directory. OS-level credential storage provides user-session binding and
OS-managed access control.

The current dev mode operates without any authentication requirement — this is intentional for
single-user local development. The authentication interface must be a no-op stub in dev so that
no existing tests break and no new gate is created before the managed endpoint is qualified.

---

## Decision

Adopt a two-tier `AuthProvider` interface:

1. **DevAuthStub** — always returns `True` for `is_authenticated()`; all credential operations are
   no-ops. Active when `STS_OS_AUTH_ENABLED=false` (default). Safe for CI, synthetic testing, and
   single-user local deployments.

2. **WindowsCredentialLockerProvider** — uses `CredWrite`/`CredRead`/`CredDelete` via
   `ctypes.windll.advapi32`. Active only when `STS_OS_AUTH_ENABLED=true` **and** `platform.system()
   == "Windows"`. Raises `RuntimeError` on non-Windows to prevent accidental enablement.

**Credential storage details:**
- Target name prefix: `Verbatim/` (e.g., `Verbatim/secret_ref_key`)
- Credential type: `CRED_TYPE_GENERIC` (1)
- Persistence: `CRED_PERSIST_LOCAL_MACHINE` (2) — per-machine, per-user
- Blob encoding: UTF-8
- `CredFree` called in `finally` block to prevent memory leaks

**Auth is NOT enforced in `app.py` at this time.** Enforcement wiring is a separate increment
that requires QG-03 managed-endpoint qualification first. This ADR establishes the contract and
stub; the enforcement decision is deferred to the QG-03 gate.

---

## Interface

```python
class AuthProvider(ABC):
    def is_authenticated(self) -> bool: ...
    def get_credential(self, key: str) -> str | None: ...
    def store_credential(self, key: str, value: str) -> None: ...
    def delete_credential(self, key: str) -> None: ...

def get_auth_provider() -> AuthProvider:
    # Returns DevAuthStub unless STS_OS_AUTH_ENABLED=true on Windows
```

---

## Threat vectors and controls

| Threat | Vector | Control |
|--------|--------|---------|
| Credential disclosure | Logging `value` arg in `store_credential` | Value never referenced after CredWrite call; not in any log or audit record |
| Dev stub active in prod | `STS_OS_AUTH_ENABLED` not set on managed endpoint | IT must set `STS_OS_AUTH_ENABLED=true` as part of QG-03 endpoint config |
| Non-Windows enablement | Developer sets `STS_OS_AUTH_ENABLED=true` on macOS/Linux | Factory raises `RuntimeError` immediately |
| Credential theft via memory | In-memory value between `get_credential` and use | Acceptable residual risk; managed endpoint adds OS-level memory protections |
| `CredFree` omission (memory leak) | Exception in `get_credential` before free | `CredFree` in `finally` block |
| Target name collision | Two apps using same `Verbatim/` prefix | Unique prefix; IT namespace policy applies |

---

## Rejected alternatives

| Alternative | Reason rejected |
|-------------|----------------|
| Environment variable secrets | Appear in `os.environ` dumps, shell history, and process listings |
| Plaintext config file | Readable by any process with user privilege; backed up to cloud |
| SQLite credential store | Custom encryption required; no OS session binding |
| DPAPI-encrypted file | Overlaps with audit store design (ADR-007); duplicates complexity |

---

## Open items for QG-03 managed-endpoint qualification

1. **Audit logging** of credential access events — currently no record of `get_credential` calls.
   ADR-007 AuditStore does not cover auth events (content-free requirement prevents it). A separate
   Windows Event Log entry may be required by IT policy.
2. **Key rotation procedure** — how `store_credential` is called when a secret changes.
3. **Backup exclusion** — Windows Credential Locker is included in roaming profiles by default on
   some configurations. IT must verify `CRED_PERSIST_LOCAL_MACHINE` is honored.
4. **Enforcement wiring** — `app.py` must check `auth_provider.is_authenticated()` on protected
   endpoints once QG-03 qualifies the endpoint. This is a separate story.

---

## Consequences

- `src/secure_transcribe/auth.py` provides the `AuthProvider` ABC and both implementations.
- `Settings.os_auth_enabled` field tracks the configured state (env: `STS_OS_AUTH_ENABLED`).
- Existing tests are unaffected — `DevAuthStub` is always-True and never touches the filesystem.
- 12 new tests in `tests/test_auth.py` cover the contract, env var gating, and platform guard.
- QG-03 cannot close until: service identity configured, Locker tested on managed endpoint, and
  enforcement wiring merged and pen-tested.
