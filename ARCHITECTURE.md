# Verbatim architecture

This package defines the implemented architecture at three abstraction levels and binds each important claim to a deterministic evaluation. It describes the current single-user Windows MVP, not a future multi-user service or a compliance certification.

| Level | Decision scope | Canonical definition | Rendered view |
|---|---|---|---|
| L1 | People, system boundary, external dependencies, and trust boundaries | [L1 system context](architecture/L1_SYSTEM_CONTEXT.md) | [SVG](diagrams/l1-system-context.svg) / [PNG](diagrams/l1-system-context.png) / [editable Mermaid](diagrams/l1-system-context.mmd) |
| L2 | Runtime containers, stores, protocols, and deployment boundary | [L2 container architecture](architecture/L2_CONTAINER_ARCHITECTURE.md) | [SVG](diagrams/l2-container-architecture.svg) / [PNG](diagrams/l2-container-architecture.png) / [editable Mermaid](diagrams/l2-container-architecture.mmd) |
| L3 | Components, interfaces, state machines, data contracts, and failure behavior | [L3 component architecture](architecture/L3_COMPONENT_ARCHITECTURE.md) | [SVG](diagrams/l3-component-architecture.svg) / [PNG](diagrams/l3-component-architecture.png) / [editable Mermaid](diagrams/l3-component-architecture.mmd) |

The executable gate catalog is [architecture-evals.json](evals/architecture-evals.json). The evaluation policy, thresholds, and interpretation rules are in [EVALUATION_MODEL.md](architecture/EVALUATION_MODEL.md). Run:

```powershell
python scripts\validate_architecture.py
```

The validator fails closed if a required artifact, component, symbol, test, dependency rule, or diagram is missing. Critical gates are conjunctive: one failed critical gate blocks architecture validation; a weighted score cannot hide it. The current evidence packet is [architecture-eval-report.json](evidence/architecture/architecture-eval-report.json).

## System invariants

1. The service binds to loopback only and does not require a network data plane.
2. MP4, paths, metadata, model output, transcript text, and tool output are untrusted.
3. Consent, request-token, upload, path, format, duration, file-count, byte, timeout, storage, and state controls are deterministic.
4. FFmpeg and Whisper receive fixed local arguments and bounded elapsed budgets.
5. Model output is schema-validated before durable use; analysis is deterministic and never executes transcript instructions.
6. Durable job data uses UUID-scoped managed directories. Batch output stays inside an approved root and never overwrites an existing file.
7. Job and batch work reaches a visible terminal state. Temporary audio is removed on success, failure, cancellation, or timeout.
8. Audit metadata excludes media and transcript content. External exports remain outside managed deletion and must follow organizational records controls.
9. Manifest preview is disabled by default, accepts only a bounded CSV/XLSX subset, stores plans in expiring process memory, redacts credential targets, and cannot acquire or process media.

## Architecture decision records

- [ADR-001: local-only single-user deployment](architecture/decisions/ADR-001-local-only-single-user.md)
- [ADR-002: deterministic controls and fail-closed evaluation](architecture/decisions/ADR-002-deterministic-controls.md)
- [ADR-003: managed storage and external export boundary](architecture/decisions/ADR-003-storage-export-boundary.md)
- [ADR-004: bounded, memory-only manifest preview](architecture/decisions/ADR-004-bounded-manifest-preview.md)
