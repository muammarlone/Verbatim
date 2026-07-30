# ADR-001: local-only single-user deployment

- Status: accepted
- Date: 2026-07-29

## Decision

Deploy Verbatim as a loopback-only utility for one authorized operator on a managed endpoint. Keep media, model inference, storage, analysis, and export generation local. Do not add a network listener, remote model, cloud queue, telemetry service, shared account, or runtime download path in this MVP.

## Consequences

The architecture avoids a cloud media data plane and keeps consent/deletion visible to the operator. It does not provide OS-user isolation, centralized records enforcement, remote administration, or proof that the endpoint itself is secure. IT must supply ACLs, disk encryption, egress controls, patched dependencies, and an approved model.
