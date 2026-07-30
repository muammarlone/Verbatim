# Security Guide

## Intended boundary

Verbatim is a single-user, local endpoint application. It does not authenticate multiple users and must not be exposed on a LAN, VPN, reverse proxy, or public interface. The CLI fixes the host to `127.0.0.1` and rejects non-loopback binds.

## Implemented controls

- Trusted host allowlist and loopback-only launcher.
- Per-process request token for upload, batch creation, and deletion mutations.
- No CORS enablement, cloud APIs, telemetry, remote fonts, or CDNs.
- Content Security Policy, frame denial, MIME sniffing denial, no-referrer policy, and browser permission denial.
- Extension, MIME, signature, duration, and audio-track validation.
- Pre-parser request-body limit plus streaming upload limit, media duration limit, local job cap, one transcription at a time, and elapsed-time budgets.
- One configured batch-workspace root; relative path containment; link/junction, traversal, recursion, file-count, combined-byte, filename-collision, and overwrite guards.
- UUID-only storage paths, atomic JSON writes, atomic no-overwrite batch-output publication, stable error envelopes, model SHA-256 provenance, and content-free audit events.
- Batch monitor failures reach a visible terminal state instead of silently abandoning work.
- Temporary audio cleanup, terminal-state-only job deletion, batch-owned-job protection, and explicit retention sweep.
- Disabled-by-default manifest preview with mutation token, dual 5 MiB request limits, strict seven-column CSV/XLSX parsing, hostile ZIP/XML feature rejection, 25-row cap, expiring process-memory plans, credential-target redaction, and metadata-only audit.

## Required deployment controls

- Install from an approved, scanned wheelhouse and FFmpeg package.
- Store `STS_DATA_DIR` on an encrypted volume with a per-user/service-account ACL.
- Set `STS_BATCH_ROOT` to a separate approved encrypted workspace with the same least-privilege ACL discipline.
- Provision the model through approved software distribution and record its SHA-256.
- Use endpoint protection, OS patching, controlled backups, and an incident owner.
- Disable backup/indexing of the data directory unless policy explicitly authorizes it.
- Validate retention requirements; the built-in seven-day value is a default, not a legal policy.

## Known residual risks

- A process running as the same OS identity can read local job files or call the loopback API.
- MP4 parsing and ML runtimes are complex native attack surfaces; sandboxing is not included.
- The app has not completed formal penetration testing, accessibility certification, privacy impact assessment, or records-management review.
- Deletion cannot remove copies already exported, backed up, indexed, or captured by endpoint tools.
- Batch cleanup removes managed copies and metadata, not original input files or requested output-folder files; those remain governed by organizational records and DLP controls.
- Atomic batch-output publication requires same-directory hard-link support. An unsupported or unhealthy output filesystem fails closed without replacing an existing file; IT must qualify the approved workspace before pilot use.
- Transcript mistakes may materially change meaning. Human review is mandatory before consequential use.
- Manifest preview does not unlock archives, resolve credentials, call Zoom, create jobs, or prove a referenced recording is authorized or authentic. Those paths remain unimplemented and disabled pending their separate gates.

If unauthorized access, wrong-user data, failed deletion propagation, or missing audit evidence is observed, stop using the utility, preserve non-content incident metadata, and escalate to the organization’s security/privacy owner.
