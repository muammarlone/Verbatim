# ADR-003: managed storage and external export boundary

- Status: accepted
- Date: 2026-07-29

## Decision

Store working data under UUID-scoped managed job and batch directories. Remove managed source and derived artifacts through explicit deletion and startup retention. Treat user-requested exports in the approved batch output folder as external copies: publish atomically without overwrite, preserve provenance, and disclose that application cleanup does not delete them.

## Consequences

Managed cleanup is bounded and testable. Exported copies can outlive application state and are governed by endpoint ACL, DLP, backup, and records processes. Production approval therefore requires IT and records owners to qualify the configured directories and lifecycle.
