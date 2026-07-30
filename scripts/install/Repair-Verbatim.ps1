<#
.SYNOPSIS
    Preparatory stub for Verbatim installation repair.

.DESCRIPTION
    THIS IS A PREPARATORY STUB. IT must complete on a managed clean-machine endpoint.
    Repair re-verifies all hashes, re-stages missing files, and re-runs the post-install
    smoke test. It must not modify transcript data or user configuration.

.NOTES
    Linked story: STS-110, STS-117  |  Gate: QG-02  |  Risk: R-17
    Status: PREPARATORY STUB — not for production use
#>

#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$InstallDir = "C:\Program Files\Verbatim"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:VERBATIM_INSTALLER_PRODUCTION_READY -ne 'signed-and-qualified') {
    Write-Error "STOP: Preparatory stub. Not for production use."
    exit 1
}

Write-Warning "TODO (IT): Re-verify FFmpeg and model hashes from sbom/hash-manifest.json."
Write-Warning "TODO (IT): Re-stage any missing application files without touching transcript data."
Write-Warning "TODO (IT): Re-run post-install smoke test and record repair evidence."

Write-Host "Repair stub complete. All TODO items must be completed before use in production."
