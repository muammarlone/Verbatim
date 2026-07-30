# ADR-002: deterministic controls and fail-closed evaluation

- Status: accepted
- Date: 2026-07-29

## Decision

Use deterministic code for consent, authorization token checks, path containment, input/schema validation, budgets, state transitions, retention, deletion, provenance, and architecture evaluation. Transcript analysis remains deterministic and extractive. An LLM judgment cannot replace these controls or convert a failed critical gate into a pass.

## Consequences

Controls are reproducible and can be regression-tested without a model. The feature set is narrower: there is no generative summary or semantic interpretation. Architecture drift blocks validation until the implementation, definition, and evidence agree.
