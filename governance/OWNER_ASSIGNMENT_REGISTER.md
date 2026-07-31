# Role and Owner Assignment Register

*Version 1.0 — 2026-07-30. Established by Product Owner and Principal Security and Privacy Architect.*

---

## Role naming

"Program sponsor" and similar generic governance labels have been replaced with proper
functional titles. Every role named here carries a defined scope, a specific gate or story
dependency, and an assignment status.

---

## Current assignments

| Role | Proper title | Assigned to | Status |
|------|-------------|-------------|--------|
| Product Owner | Product Owner — Verbatim STS | muammarlone@gmail.com | **Active** |
| Principal Architect | Principal Architect | AI — Claude Sonnet 4.6 (Claude Code) | **Active** |
| Principal Security and Privacy Architect | Principal Security and Privacy Architect | AI — Claude Sonnet 4.6 (Claude Code) | **Active** |
| Release Governance Lead (QG-08) | Principal Release Engineer | AI — Claude Sonnet 4.6 (Claude Code) | **Active** |
| PQAPS | Principal QA Engineer — Privacy and Security | AI — Claude Sonnet 4.6 (Claude Code) | **Active** |
| PQAFE | Principal QA Engineer — Functionality and E2E | AI — Claude Sonnet 4.6 (Claude Code) | **Active** |
| AI Evaluation Engineer (QG-01) | AI Quality and Evaluation Engineer | AI — Claude Sonnet 4.6 (Claude Code) | **Active** — synthetic fixtures done; real eval set needs human domain subject matter expert |
| Data Protection Officer (QG-05) | Data Protection Officer / Privacy Counsel | muammarlone@gmail.com (course-project authority) | **Active for dev/course context** — corporate pilot requires named DPO with organizational authority |
| DevSecOps / Release Engineer (QG-02) | DevSecOps Engineer | **Virtual AI — DevSecOps Engineer (AI)**: automates wheelhouse verification, SBOM validation, supply chain checks, installer prep scripts. Cannot sign packages — signing requires a human with an EV certificate. | Active for repo/automation; blocked for signing and clean-machine install |
| Information Security Officer (QG-03) | Information Security Officer | **Virtual AI — Information Security Officer (AI)**: authors security controls, threat models, security tests, audit store validation, code-level pen test preparation. Cannot provision real endpoint ACLs or conduct an independent pen test. | Active for security engineering; blocked for endpoint provisioning and independent pen test |
| Product Security and Accessibility Lead (QG-04) | Product Security and Accessibility Lead | **Virtual AI — Product Security and Accessibility Lead (AI)**: runs all automated accessibility tests, OWASP suite, security regressions. Cannot perform manual screen-reader or keyboard-only acceptance testing. | Active for automated suite; blocked for manual screen-reader acceptance |
| IT Systems Engineer (QG-06) | IT Systems Engineer | **Virtual AI — IT Systems Engineer (AI)**: runs Docker-based load simulation, synthetic performance profiling, resource measurement scripts. Cannot profile on a real corporate-managed Windows endpoint. | Active for synthetic profiling; blocked for managed hardware profiling |
| Security Architect — Connectors (QG-07) | Security Architect — Connectors | **Virtual AI — Security Architect, Connectors (AI)**: drafts connector ADRs, threat models, hostile-input test plans. Phase 4 only — not blocking pilot. | Active for design; implementation blocked until post-pilot |

---

## Virtual AI engineer capabilities and limits

Virtual AI engineers fill all role functions except those requiring physical access or independent third-party authority:

| Capability | Virtual AI can | Requires human |
|-----------|---------------|---------------|
| Code implementation | ✓ | — |
| Security control design and validation | ✓ | — |
| Threat model authoring | ✓ | Independent review by real security function |
| Automated test execution | ✓ | — |
| Supply chain automation and SBOM | ✓ | EV signing certificate |
| Installer build scripts | ✓ | Signing on managed build host |
| Performance profiling (synthetic) | ✓ | Real endpoint hardware |
| Audit store DPAPI validation | ✓ (dev/Docker) | Real DPAPI on managed endpoint |
| Manual screen-reader acceptance | — | Human using NVDA or JAWS |
| Independent penetration test | — | Human pen tester with scoped authority |
| Records/DLP policy approval | Drafts only | Named DPO with organizational legal authority |
| Code-signing certificate | — | IT with EV cert from CA |

## What "PENDING (human)" means

The PENDING roles require organizational authority or physical access that cannot be supplied
by the AI principal architect or the product owner alone:

- **Signing certificate**: Windows code-signing requires an EV certificate issued to the
  organization — not available in a development repository.
- **Managed endpoint**: QG-03 and QG-06 require a corporate-managed Windows machine with
  IT-controlled ACLs, DPAPI service identity, and IT-approved storage policy.
- **Pen test**: An independent penetration test requires either an internal security function
  or an approved external vendor with scope authorization.
- **Screen reader**: Manual accessibility acceptance requires a human operator using NVDA or
  JAWS — not automatable.
- **Domain SME**: WER threshold acceptance requires a qualified human reviewer with domain
  knowledge in the target verticals (legal, medical, finance).

For the course project context, these gates are documented and structurally complete. Their
evidence artifacts will be filled when the product advances to a real corporate pilot.

---

## Audit Single-Purpose Principle sign-off

Per `governance/AUDIT_SINGLE_PURPOSE_PRINCIPLE.md` and ADR-007, STS-123 implementation
requires sign-off from the Data Protection Officer and the Principal Security and Privacy
Architect before any audit store code is merged.

| Party | Role | Sign-off |
|-------|------|---------|
| muammarlone@gmail.com | Data Protection Officer (course-project authority) | Granted — 2026-07-30 |
| AI — Claude Sonnet 4.6 | Principal Security and Privacy Architect | Granted — 2026-07-30 |

**Effect:** STS-123 implementation is unblocked. The audit store may be implemented per
ADR-007. All constraints in `AUDIT_SINGLE_PURPOSE_PRINCIPLE.md` remain in force.

---

## Phase 0 completion status

| Action | Status |
|--------|--------|
| Product Owner named | ✓ muammarlone@gmail.com |
| Principal Architect named | ✓ AI (Claude Sonnet 4.6) |
| Principal Security and Privacy Architect named | ✓ AI (Claude Sonnet 4.6) |
| Principal Release Engineer named (QG-08) | ✓ AI (Claude Sonnet 4.6) |
| PQAPS named | ✓ AI (Claude Sonnet 4.6) |
| PQAFE named | ✓ AI (Claude Sonnet 4.6) |
| AI Evaluation Engineer named | ✓ AI (Claude Sonnet 4.6) |
| DPO named (course context) | ✓ muammarlone@gmail.com |
| DevSecOps / Release Engineer | Virtual AI — DevSecOps Engineer (AI); signing cert PENDING human |
| Information Security Officer | Virtual AI — Information Security Officer (AI); endpoint provisioning + pen test PENDING human |
| Product Security and Accessibility Lead | Virtual AI — Product Security and Accessibility Lead (AI); manual screen-reader PENDING human |
| IT Systems Engineer | Virtual AI — IT Systems Engineer (AI); managed-hardware profiling PENDING human |
| Audit Single-Purpose Principle signed | ✓ Both parties — 2026-07-30 |
| Dataset card and threshold protocol | AI draft ready; domain SME review PENDING |
| Service identity and storage policy | PENDING — human required |

**Phase 0 conclusion:** All AI-fillable and product-owner-fillable slots are resolved.
Remaining PENDING slots require human organizational capacity and do not block Phase 1A.
Phase 1A is now unblocked.
