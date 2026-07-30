# ADR-005: Windows Installer Packaging — MSIX versus WiX/MSI

**Status:** Proposed — pending IT packaging and security lead approval

**Date:** 2026-07-30

**Linked story:** STS-110, STS-117

**Linked risk:** R-17

---

## Decision

This record documents the packaging trade-off for distribution of Verbatim to managed Windows
endpoints. A formal decision requires sign-off from the IT packaging and security lead; this
document supplies the analysis and recommended option only.

---

## Context and constraints

Verbatim is a local-first desktop application. It requires:

- A Python runtime and the packages listed in `sbom/requirements.lock`.
- `openai-whisper` and its ML dependencies (torch, numba, numpy, tiktoken, more-itertools),
  which must be pre-staged offline because Torch alone exceeds 2 GiB.
- FFmpeg (an approved, patched build) placed on the system PATH or in a declared location.
- A Whisper model artifact (`.pt` file) placed in a declared model directory.
- No network egress after installation; no cloud dependencies at runtime.

Distribution must support:
- Intune and Configuration Manager (MECM) deployment to managed Windows 10/11 endpoints.
- Per-machine installation (not per-user) to support managed service identities.
- Silent install, silent repair, silent upgrade, and clean uninstall with rollback.
- Hash attestation for the package, model, FFmpeg binary, and Python environment.
- Log redaction — no transcript paths, content, or user data in installer logs.

---

## Options

### Option A: MSIX with MSIX Packaging Tool or Advanced Installer

MSIX is Microsoft's recommended packaging format for modern Windows deployment.

| Criterion | Assessment |
|---|---|
| Intune support | Native — MSIX is the preferred format for Intune LOB app deployment. |
| MECM support | Supported via the application deployment wrapper; MSIX supersedes MSI for new apps. |
| Per-machine install | Requires provisioned-package flow (`dism /Add-ProvisionedAppxPackage`) or machine-wide deployment context. Per-user is the default; per-machine needs documented configuration. |
| Signing requirement | All MSIX packages must be signed. Development packages can use a self-signed cert on dev machines; production requires a code-signing cert trusted by the managed endpoint. |
| Offline model/FFmpeg staging | MSIX cannot bundle large binaries (>2 GiB limit per package file). Torch and the model artifact must be provisioned separately (PowerShell bootstrap or Configuration Manager package). |
| Repair | Built-in via `dism /RestoreProvisionedAppxPackage` or Store/Intune reinstall. |
| Rollback | Supported by provisioning flow; prior MSIX version can be re-provisioned. |
| Log redaction | Installer log location is controlled; content logging would be custom code only. |
| Complexity | Higher — requires VHD or clean Windows container for capture; virtual environments complicate capture. |

ASSUMPTION: Intune or MECM is the deployment mechanism. If endpoints use a different MDM or are
unmanaged, MSIX provisioning flows change materially.

### Option B: WiX Toolset v4 MSI

WiX is the de facto standard for traditional Windows MSI authoring, widely used in enterprise IT.

| Criterion | Assessment |
|---|---|
| Intune support | Supported (Intune LOB app with `.msi`). |
| MECM support | Native — MSI is the historical MECM standard. |
| Per-machine install | Default behavior for MSI (ALLUSERS=1). Straightforward. |
| Signing requirement | MSI must be Authenticode-signed for deployment on managed endpoints. Development builds can be unsigned on dev machines. |
| Offline model/FFmpeg staging | WiX supports multi-component packages. Large artifacts (Torch, model) can be included as separate Merge Modules or bootstrapped via WiX Burn. Burn can chain a Python installer, wheelhouse installer, and Verbatim MSI. |
| Repair | MSI repair built-in (`msiexec /f`). |
| Rollback | MSI rollback built-in. |
| Log redaction | MSI logging is controlled by `MSILOGGINGMODE`; verbose logging requires explicit opt-in. |
| Complexity | Moderate — WiX 4 has a learning curve; Burn bootstrapper adds complexity but is well-documented. |

### Option C: WiX Burn bootstrapper with embedded Python and wheelhouse

A specialization of Option B where the Burn bootstrapper chains:
1. An embedded Python 3.12 redistributable (if not already present at target version).
2. An offline wheelhouse installer (runs `pip install --no-index --find-links wheelhouse/`).
3. The Verbatim WiX MSI.
4. A post-install step to stage the model and FFmpeg to declared locations.

This separates the large ML assets (model, Torch wheels) from the Verbatim application package,
allowing IT to stage model updates without reinstalling the full application.

---

## Evaluation

| Criterion | MSIX (A) | WiX MSI (B) | WiX Burn + wheelhouse (C) |
|---|---|---|---|
| Intune native support | Preferred | Supported | Supported |
| MECM native support | Supported | Native | Native |
| Per-machine default | Requires configuration | Default | Default |
| Large ML artifact handling | Requires separate provisioning | Merge modules or chained packages | Purpose-built: offline wheelhouse chain |
| Python environment isolation | Challenging to capture | WiX custom action or embedded Python | Embedded Python redistributable |
| Repair | Built-in | Built-in | Built-in (per component) |
| Rollback | Re-provision | Built-in | Built-in |
| Signing requirement | Mandatory, strict | Mandatory | Mandatory |
| IT familiarity in most enterprises | Growing | Established | Established |
| Estimated build complexity | High | Moderate | Moderate–high |

---

## Recommendation

RECOMMENDATION: **Option C — WiX Burn bootstrapper with embedded Python and offline wheelhouse**,
unless IT confirms MSIX provisioning is already established for large per-machine Python
applications on the managed endpoint.

Rationale:
1. WiX MSI with Burn provides the most mature path for per-machine Python application deployment
   with large offline dependency bundles on managed Windows endpoints.
2. Separating the ML artifact stage (model, Torch wheelhouse) from the application MSI allows
   model updates without a full application reinstall — operationally important given Whisper
   model file sizes.
3. MSIX is preferred by Microsoft but per-machine Python environments with multi-gigabyte assets
   are not a common MSIX use case; IT packaging complexity and capture environment requirements
   are higher.
4. Both options require a code-signing certificate from the organization's PKI. This ADR does
   not change that constraint.

This recommendation is invalidated if:
- IT confirms MSIX per-machine provisioning is already standardized in the environment.
- The organization uses a software distribution mechanism that handles Python environments
  natively (e.g., conda-based packages, Chocolatey, or an existing internal package manager).
- Security review identifies a WiX-specific vulnerability in the approved build-tool version.

---

## Consequences

Regardless of option chosen:

- The Python runtime version and wheel hashes must be pinned in `sbom/requirements.lock` and
  attested in `sbom/hash-manifest.json` before any installer is submitted to IT.
- The model artifact SHA-256 and FFmpeg binary SHA-256 must be recorded in
  `sbom/hash-manifest.json` at the qualified endpoint.
- Install, repair, upgrade, uninstall, and rollback scripts in `scripts/install/` are
  preparatory stubs; IT must run them on clean managed images and supply signed evidence.
- The signed package must not be called a production release until QG-02 exit criteria are met.

---

## Open questions (IT packaging lead to resolve)

1. Is MSIX or MSI the organizational standard for Intune LOB app deployment on managed
   Windows 11 endpoints?
2. Does the existing code-signing PKI issue EV certificates, or standard OV? (MSIX requires
   trusted signing for provisioned packages.)
3. What is the approved Python redistributable source? (python.org embedded distribution,
   WinPython, or a corporate-approved redistributable?)
4. Is there an organizational standard for staging large ML model artifacts separate from
   application installers?
5. What is the approved FFmpeg build? (Must be patched, loopback-only argument enforcement
   verified, and hash attested before use in production.)

---

## References

- WiX Toolset v4: https://wixtoolset.org/docs/
- Microsoft MSIX documentation: https://learn.microsoft.com/en-us/windows/msix/
- Intune Win32 app deployment: https://learn.microsoft.com/en-us/mem/intune/apps/apps-win32-app-management
- `sbom/requirements.lock` — pinned transitive dependency set
- `sbom/hash-manifest.json` — hash manifest schema and known hashes
- `sbom/vulnerability-disposition.json` — per-package advisory disposition
- `governance/RISK_REGISTER.md` R-17 — supply chain and installer privilege risk
