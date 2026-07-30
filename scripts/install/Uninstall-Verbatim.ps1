<#
.SYNOPSIS
    Preparatory stub for Verbatim uninstallation.

.DESCRIPTION
    THIS IS A PREPARATORY STUB. IT must complete on a managed clean-machine endpoint.
    Uninstall removes the application, Python environment, FFmpeg, and all derived artifacts.
    It must NOT delete user-owned export files (the operator owns those).
    It must deregister from Windows registry and verify clean state.

.NOTES
    Linked story: STS-110, STS-117  |  Gate: QG-02  |  Risk: R-17
    Status: PREPARATORY STUB — not for production use
#>

#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$InstallDir = "C:\Program Files\Verbatim",
    [switch]$PreserveUserExports
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:VERBATIM_INSTALLER_PRODUCTION_READY -ne 'signed-and-qualified') {
    Write-Error "STOP: Preparatory stub. Not for production use."
    exit 1
}

Write-Warning "TODO (IT): Stop and remove Verbatim service/process if running."
Write-Warning "TODO (IT): Remove application, Python env, model, and FFmpeg from $InstallDir."
Write-Warning "TODO (IT): Deregister uninstall key from HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Verbatim."
Write-Warning "TODO (IT): If -PreserveUserExports is NOT set, inform user that exported files in user directories are NOT removed by the uninstaller (they are user-owned)."
Write-Warning "TODO (IT): Record uninstall evidence with revision, date, and endpoint identifier."

Write-Host "Uninstall stub complete. All TODO items must be completed before use in production."
