<#
.SYNOPSIS
    Create the MSIX directory layout for the Verbatim STS installer.

.DESCRIPTION
    Creates the MSIX directory layout and AppxManifest.xml from the template.
    Does NOT self-sign. Signing requires an EV certificate held by IT.

    GUARD: VERBATIM_INSTALLER_PRODUCTION_READY must be set to 'signed-and-qualified'
    by IT before this script may proceed. This script must not and does not
    self-assign that value.

.PARAMETER OutputDir
    Directory for the MSIX layout. Default: dist/installer relative to repo root.

.PARAMETER Version
    Application version string. Default: 1.0.0.0

.NOTES
    Story:    STS-110
    Gate:     QG-02
    ADR:      architecture/decisions/ADR-005-windows-installer-packaging.md
    Status:   BUILD SCRIPT — requires IT EV signing certificate to produce valid package
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$OutputDir = "",
    [string]$Version = "1.0.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Guard: VERBATIM_INSTALLER_PRODUCTION_READY must be set by IT
# This script must NOT self-assign the bypass value.
# ---------------------------------------------------------------------------
if ($env:VERBATIM_INSTALLER_PRODUCTION_READY -ne 'signed-and-qualified') {
    Write-Error @"
STOP: VERBATIM_INSTALLER_PRODUCTION_READY must be set to 'signed-and-qualified' by IT
before this script may create an installer layout.

This value must be set externally by IT with an EV signing certificate in hand.
This script does not and must not self-assign this value.

Next steps for IT:
  1. Obtain an EV code-signing certificate from an approved CA.
  2. Complete the offline wheelhouse (scripts/build/build_offline_wheelhouse.ps1).
  3. Set VERBATIM_INSTALLER_PRODUCTION_READY=signed-and-qualified in the build environment.
  4. Run this script to produce the MSIX layout.
  5. Sign the MSIX package: signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 /f cert.pfx /p password VerbatimSTS.msix
  6. Record the signed package SHA-256 in evidence/installer/.
"@
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..") | Select-Object -ExpandProperty Path
$TemplateDir = Join-Path $PSScriptRoot "templates"
$Dest = if ($OutputDir) { $OutputDir } else { Join-Path $RepoRoot "dist\installer\msix" }

Write-Host "MSIX layout output: $Dest"
Write-Host "Version:            $Version"
Write-Host ""

# ---------------------------------------------------------------------------
# Create directory structure
# ---------------------------------------------------------------------------
$dirs = @(
    $Dest,
    (Join-Path $Dest "Assets"),
    (Join-Path $Dest "VerbatimSTS")
)
foreach ($d in $dirs) {
    if ($PSCmdlet.ShouldProcess($d, "Create directory")) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }
}

# ---------------------------------------------------------------------------
# Copy and version AppxManifest.xml
# ---------------------------------------------------------------------------
$templatePath = Join-Path $TemplateDir "AppxManifest.xml"
$manifestDest = Join-Path $Dest "AppxManifest.xml"

if (-not (Test-Path $templatePath)) {
    Write-Error "Template not found: $templatePath"
    exit 1
}

$content = Get-Content $templatePath -Raw
$content = $content -replace 'Version="1.0.0.0"', "Version=`"$Version`""

if ($PSCmdlet.ShouldProcess($manifestDest, "Write AppxManifest.xml")) {
    Set-Content -Path $manifestDest -Value $content -Encoding utf8
    Write-Host "AppxManifest.xml written: $manifestDest"
}

# ---------------------------------------------------------------------------
# Write placeholder asset files (IT replaces with real icons)
# ---------------------------------------------------------------------------
$placeholderNote = "PLACEHOLDER: Replace with signed production icon before packaging."
foreach ($asset in @("StoreLogo.png", "Square150x150Logo.png", "Square44x44Logo.png")) {
    $assetPath = Join-Path $Dest "Assets\$asset"
    if (-not (Test-Path $assetPath)) {
        if ($PSCmdlet.ShouldProcess($assetPath, "Write placeholder asset")) {
            Set-Content -Path $assetPath -Value $placeholderNote -Encoding utf8
        }
    }
}

# ---------------------------------------------------------------------------
# Write build log
# ---------------------------------------------------------------------------
$logDir = Join-Path $RepoRoot "dist\installer"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$buildLog = [PSCustomObject]@{
    schema_version     = "1.0"
    generated_at       = (Get-Date -Format "o")
    script             = "scripts/build/build_msix.ps1"
    version            = $Version
    output_dir         = $Dest
    guard_env          = "VERBATIM_INSTALLER_PRODUCTION_READY"
    guard_value_set    = $true
    outcome            = "layout_created_unsigned"
    next_step          = "IT must sign the MSIX package with an EV certificate using signtool.exe"
    signing_not_done   = $true
}
$logPath = Join-Path $logDir "build-log.json"
$buildLog | ConvertTo-Json -Depth 3 | Set-Content -Path $logPath -Encoding utf8

Write-Host ""
Write-Host "MSIX layout created at: $Dest"
Write-Host "Build log written:      $logPath"
Write-Host ""
Write-Host "NEXT STEP (IT): Sign the package with an EV certificate:"
Write-Host '  signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 /f cert.pfx VerbatimSTS.msix'
Write-Host ""
Write-Host "Do NOT distribute unsigned packages."
