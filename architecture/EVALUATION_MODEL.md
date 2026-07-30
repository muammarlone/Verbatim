# Architecture evaluation model

## Objective

Architecture validation answers one narrow question: does the checked-out implementation and its evidence still satisfy the declared L1-L3 contracts? It does not certify production security, transcription accuracy, accessibility, legal compliance, or operational readiness on an untested endpoint.

## Evaluation design

The canonical catalog is `evals/architecture-evals.json`. Each gate has a stable ID, architecture level, criticality, deterministic check type, threshold, evidence references, and failure action. `scripts/validate_architecture.py` evaluates the catalog without a model or network call.

Check types:

| Type | What is evaluated | Pass rule |
|---|---|---|
| `files_exist` | Architecture, security, governance, rendered diagrams, and evidence sources | Every declared path exists and is non-empty |
| `symbols_exist` | Required boundary/control components | Every declared Python symbol is present in the AST |
| `source_contains` | Fixed security/configuration contracts that are not exposed as symbols | Every literal fragment exists in the declared source file |
| `forbidden_imports_absent` | Production network/cloud dependency boundary | No production Python import matches a forbidden prefix |
| `module_dependencies` | L2/L3 internal dependency graph | Every internal import is allowed and no forbidden edge exists |
| `tests_exist` | Traceability from claims to executable regression cases | Every named test function exists in the declared test module |
| `json_contract` | Versioned evidence/schema integrity | Declared JSON files parse and contain required keys/values |

## Gate catalog

| Level | Gate group | Intent | Required outcome |
|---|---|---|---|
| L1 | Privacy and security | Preserve the local-only, single-user, bounded trust boundary | All critical L1 gates pass |
| L1 | Governance and operations | Keep consent, claim boundaries, readiness, retention, and audit traces explicit | All critical L1 gates pass |
| L2 | Containers and dependencies | Keep runtime responsibilities mapped and prevent unapproved coupling/network clients | All critical L2 gates pass |
| L2 | Reliability and storage | Preserve timeouts, capacity controls, terminal states, atomic/no-overwrite persistence | All critical L2 gates pass |
| L3 | Components and contracts | Preserve symbols, schemas, stable errors, state and cleanup regressions | All critical L3 gates pass |
| L3 | Manifest preview | Preserve default-off, bounded parser, redaction, expiry, reason-code, and no-acquisition contracts | All critical manifest gates pass |
| Trace | Documentation and evidence | Ensure each architectural claim has a current executable/evidence reference | All trace gates pass |

## Thresholds and adjudication

- Critical pass threshold: **100%**. One failed critical evaluation blocks the aggregate decision.
- Noncritical pass threshold: **100%** for the current catalog. A future waiver must name an owner, expiry, risk ID, and compensating evidence; the validator does not silently waive failures.
- Aggregate `validated` is true only when there are zero failed gates and zero catalog errors.
- Evaluation counts are descriptive, not a maturity percentage.
- Static checks prove declared structure and traceability, not runtime behavior. Mapped pytest, smoke, browser UAT, and operational controls remain separate gates.

## Reproduction

```powershell
python scripts\validate_architecture.py
python -m pytest
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
node --check src\secure_transcribe\static\app.js
python -m build --wheel
```

The validator writes `evidence/architecture/architecture-eval-report.json` only after completing every gate. The report records catalog and validator versions, the base Git revision, a deterministic SHA-256 over evaluated source/architecture/evidence inputs, per-gate results, totals, and the final decision. The report excludes itself from the source digest, avoiding a circular hash. No raw media, transcript, credentials, request token, or hidden reasoning enters the report.

## Change and review policy

1. Add or change architecture behavior only with an updated stable eval ID or explicit rationale for reusing an existing gate.
2. Tests listed by the catalog must name the behavior they protect; generic suite existence is insufficient.
3. A generated report is evidence for one revision. It becomes stale when code or catalog changes.
4. Reviewers must inspect residual risks and UAT separately. A passing architecture report cannot convert a conditional pilot decision into production approval.
