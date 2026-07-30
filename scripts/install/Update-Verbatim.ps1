<#
.SYNOPSIS
    Preparatory stub for Verbatim upgrade.

.DESCRIPTION
    THIS IS A PREPARATORY STUB. IT must complete on a managed clean-machine endpoint.
    Upgrade verifies the new package hash, runs the installer, and verifies the result.
    It must preserve user data and configuration and support rollback to the prior version.

.NOTES
    Linked story: STS-110, STS-117  |  Gate: QG-02  |  Risk: R-17
    Status: PREPARATORY STUB — not for production use
#>

#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [string]$NewPackagePath,

    [string]$InstallDir = "C:\Program Files\Verbatim"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:VERBATIM_INSTALLER_PRODUCTION_READY -ne 'signed-and-qualified') {
    Write-Error "STOP: Preparatory stub. Not for production use."
    exit 1
}

Write-Warning "TODO (IT): Snapshot current version for rollback before starting upgrade."
Write-Warning "TODO (IT): Verify new package hash from sbom/hash-manifest.json for the candidate revision."
Write-Warning "TODO (IT): Run signed installer in silent upgrade mode."
Write-Warning "TODO (IT): Verify post-upgrade smoke test. Roll back to prior version if it fails."
Write-Warning "TODO (IT): Record upgrade evidence with old/new revision, date, and endpoint identifier."

Write-Host "Upgrade stub complete. All TODO items must be completed before use in production."
