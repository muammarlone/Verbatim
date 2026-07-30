<#
.SYNOPSIS
    Preparatory stub for clean-machine Verbatim installation.

.DESCRIPTION
    THIS IS A PREPARATORY STUB. It is not a functional installer.
    It documents the required installation steps and guard rails.
    IT packaging and security lead must complete this script on a managed
    clean-machine endpoint and supply signed evidence to close QG-02.

    Prerequisites before this script can become a production installer:
    - A signed Windows package (MSIX or MSI) per ADR-005
    - An offline wheelhouse with hash-verified wheels (sbom/requirements.lock)
    - An approved FFmpeg binary with SHA-256 recorded in sbom/hash-manifest.json
    - A Whisper model artifact with SHA-256 recorded in sbom/hash-manifest.json
    - A code-signing certificate trusted by the managed endpoint

.PARAMETER WheelhousePath
    Path to the offline pip wheelhouse directory.

.PARAMETER ModelPath
    Path to the Whisper model .pt file.

.PARAMETER FFmpegPath
    Path to the approved FFmpeg binary.

.PARAMETER InstallDir
    Per-machine installation directory. Default: C:\Program Files\Verbatim

.NOTES
    Linked story:  STS-110, STS-117
    Linked gate:   QG-02
    Linked risk:   R-17
    Status:        PREPARATORY STUB — not for production use
    ADR:           architecture/decisions/ADR-005-windows-installer-packaging.md
    Hash manifest: sbom/hash-manifest.json
#>

#Requires -RunAsAdministrator
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Container })]
    [string]$WheelhousePath,

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$ModelPath,

    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$FFmpegPath,

    [string]$InstallDir = "C:\Program Files\Verbatim"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Guard: refuse to run if PREPARATORY_STUB_BYPASS is not set to the expected sentinel.
# IT must remove this guard and complete the script before production use.
if ($env:VERBATIM_INSTALLER_PRODUCTION_READY -ne 'signed-and-qualified') {
    Write-Error "STOP: This is a preparatory stub. It must not run on a production endpoint. " +
                "Read sbom/hash-manifest.json, architecture/decisions/ADR-005-windows-installer-packaging.md, " +
                "and governance/CLAUDE_CODE_HANDOFF.md before proceeding."
    exit 1
}

function Assert-FileHash {
    param([string]$FilePath, [string]$ExpectedSha256, [string]$Label)
    if (-not $ExpectedSha256) {
        Write-Error "STOP: No expected hash recorded for $Label. Update sbom/hash-manifest.json before installing."
        exit 2
    }
    $actual = (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $ExpectedSha256.ToLower()) {
        Write-Error "STOP: Hash mismatch for $Label. Expected $ExpectedSha256 — got $actual. Do not continue."
        exit 3
    }
    Write-Host "[OK] Hash verified: $Label"
}

# Step 1: Verify FFmpeg hash
# IT must populate this value in sbom/hash-manifest.json before using this script.
$ffmpegHash = $null  # TODO: read from sbom/hash-manifest.json
Assert-FileHash -FilePath $FFmpegPath -ExpectedSha256 $ffmpegHash -Label "FFmpeg binary"

# Step 2: Verify model hash
$modelHash = $null  # TODO: read from sbom/hash-manifest.json
Assert-FileHash -FilePath $ModelPath -ExpectedSha256 $modelHash -Label "Whisper model"

# Step 3: Create per-machine install directory
if ($PSCmdlet.ShouldProcess($InstallDir, "Create installation directory")) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

# Step 4: Install Python runtime
# IT must choose the approved Python redistributable per ADR-005 and sbom/hash-manifest.json.
# Placeholder: python_installer_path must be resolved from corporate software distribution.
Write-Warning "TODO (IT): Install approved Python 3.12 runtime per-machine. Hash: see sbom/hash-manifest.json."

# Step 5: Install Python packages from offline wheelhouse
# No-index ensures no internet access during installation.
Write-Warning "TODO (IT): Run: python -m pip install --no-index --find-links '$WheelhousePath' -r requirements.txt"
# & python -m pip install --no-index --find-links $WheelhousePath -r "$PSScriptRoot\..\..\requirements.txt"

# Step 6: Copy application source to install directory
Write-Warning "TODO (IT): Copy application source to $InstallDir. Do NOT include secrets, credentials, or production recordings."

# Step 7: Stage FFmpeg to approved location
$ffmpegDest = Join-Path $InstallDir "bin\ffmpeg.exe"
if ($PSCmdlet.ShouldProcess($ffmpegDest, "Stage FFmpeg binary")) {
    Write-Warning "TODO (IT): Copy approved FFmpeg binary to $ffmpegDest after hash verification."
}

# Step 8: Stage Whisper model to approved location
$modelDest = Join-Path $InstallDir "models\$(Split-Path $ModelPath -Leaf)"
if ($PSCmdlet.ShouldProcess($modelDest, "Stage Whisper model")) {
    Write-Warning "TODO (IT): Copy Whisper model to $modelDest after hash verification."
}

# Step 9: Register application in Windows registry (per-machine)
Write-Warning "TODO (IT): Register uninstall key in HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Verbatim"

# Step 10: Verify installation
Write-Warning "TODO (IT): Run post-install smoke test and record result in evidence/quality/ with candidate revision, date, and endpoint hash."

Write-Host "Installation stub complete. All TODO items must be completed before this script is used in production."
