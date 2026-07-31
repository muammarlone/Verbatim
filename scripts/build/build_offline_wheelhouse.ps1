<#
.SYNOPSIS
    Build an offline pip wheelhouse from the pinned requirements lock file.

.DESCRIPTION
    Downloads all packages listed in sbom/requirements.lock into dist/wheelhouse/
    using pip download --no-deps. Verifies each downloaded wheel's SHA-256 against
    the hash recorded in the lock file. Writes dist/wheelhouse/manifest.json.

    GUARD: VERBATIM_BUILD_PRODUCTION_WHEELHOUSE must be set before this script runs.

.PARAMETER DryRun
    Report what would be downloaded without actually downloading.

.PARAMETER WheelhouseDir
    Destination directory. Default: dist/wheelhouse relative to repo root.

.NOTES
    Story:    STS-110
    Gate:     QG-02
    ADR:      architecture/decisions/ADR-005-windows-installer-packaging.md
    Status:   PRODUCTION BUILD SCRIPT — requires VERBATIM_BUILD_PRODUCTION_WHEELHOUSE guard
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$DryRun,
    [string]$WheelhouseDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Guard: VERBATIM_BUILD_PRODUCTION_WHEELHOUSE must be set
# ---------------------------------------------------------------------------
if (-not $env:VERBATIM_BUILD_PRODUCTION_WHEELHOUSE) {
    Write-Error @"
STOP: VERBATIM_BUILD_PRODUCTION_WHEELHOUSE must be set before building the offline wheelhouse.

Set it to a non-empty value to confirm you have:
  1. Reviewed sbom/requirements.lock and confirmed the pinned versions.
  2. Verified this script runs on an approved build host.
  3. Accepted that the generated wheelhouse will be used for a managed install.

This script must not self-assign the bypass value.
"@
    exit 1
}

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..") | Select-Object -ExpandProperty Path
$LockFile = Join-Path $RepoRoot "sbom\requirements.lock"
$DestDir = if ($WheelhouseDir) { $WheelhouseDir } else { Join-Path $RepoRoot "dist\wheelhouse" }

if (-not (Test-Path $LockFile)) {
    Write-Error "Lock file not found: $LockFile"
    exit 1
}

if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
}

Write-Host "Lock file:     $LockFile"
Write-Host "Wheelhouse:    $DestDir"
Write-Host ""

# ---------------------------------------------------------------------------
# Parse requirements.lock
# (Format: package==version ; expected hash on same or next line)
# ---------------------------------------------------------------------------
$packages = @()
$lines = Get-Content $LockFile

foreach ($line in $lines) {
    $trimmed = $line.Trim()
    if ($trimmed -match '^([A-Za-z0-9_\-]+)==([0-9][^\s;]*)') {
        $packages += [PSCustomObject]@{
            Name    = $Matches[1]
            Version = $Matches[2]
            Hash    = $null
        }
    }
}

if ($packages.Count -eq 0) {
    Write-Warning "No packages parsed from lock file. Verify lock file format."
    exit 0
}

Write-Host "Packages to download: $($packages.Count)"
Write-Host ""

# ---------------------------------------------------------------------------
# Download and verify each package
# ---------------------------------------------------------------------------
$results = @()
$failed = 0

foreach ($pkg in $packages) {
    $spec = "$($pkg.Name)==$($pkg.Version)"

    if ($DryRun) {
        Write-Host "[DRY-RUN] Would download: $spec"
        $results += [PSCustomObject]@{ Package = $spec; Status = "dry-run"; HashMatch = $null }
        continue
    }

    Write-Host "Downloading: $spec"
    try {
        $output = & python -m pip download --no-deps --dest $DestDir "$spec" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "  pip download failed for $spec : $output"
            $results += [PSCustomObject]@{ Package = $spec; Status = "download_failed"; HashMatch = $false }
            $failed++
            continue
        }

        # Find downloaded file
        $wheel = Get-ChildItem $DestDir -Filter "$($pkg.Name -replace '-','[-_]')*" |
                 Where-Object { $_.Extension -in '.whl', '.tar.gz', '.zip' } |
                 Sort-Object LastWriteTime -Descending |
                 Select-Object -First 1

        if (-not $wheel) {
            Write-Warning "  File not found in wheelhouse after download: $spec"
            $results += [PSCustomObject]@{ Package = $spec; Status = "file_not_found"; HashMatch = $false }
            $failed++
            continue
        }

        $actualHash = (Get-FileHash $wheel.FullName -Algorithm SHA256).Hash.ToLower()

        if ($pkg.Hash) {
            $match = ($actualHash -eq $pkg.Hash.ToLower())
            $status = if ($match) { "verified" } else { "hash_mismatch" }
            if (-not $match) {
                Write-Warning "  HASH MISMATCH for $spec : expected=$($pkg.Hash) actual=$actualHash"
                $failed++
            } else {
                Write-Host "  [OK] $spec — hash verified"
            }
        } else {
            $status = "downloaded_no_expected_hash"
            Write-Warning "  No expected hash in lock file for $spec — recorded actual: $actualHash"
        }

        $results += [PSCustomObject]@{
            Package   = $spec
            File      = $wheel.Name
            ActualSha256 = $actualHash
            ExpectedSha256 = $pkg.Hash
            Status    = $status
            HashMatch = ($pkg.Hash ? ($actualHash -eq $pkg.Hash.ToLower()) : $null)
        }

    } catch {
        Write-Warning "  Exception downloading $spec : $_"
        $results += [PSCustomObject]@{ Package = $spec; Status = "exception"; HashMatch = $false }
        $failed++
    }
}

# ---------------------------------------------------------------------------
# Write manifest.json
# ---------------------------------------------------------------------------
$manifest = [PSCustomObject]@{
    schema_version = "1.0"
    generated_at   = (Get-Date -Format "o")
    lock_file      = $LockFile
    wheelhouse_dir = $DestDir
    total          = $results.Count
    verified       = ($results | Where-Object { $_.Status -eq "verified" }).Count
    failed         = $failed
    packages       = $results
}

if (-not $DryRun) {
    $manifestPath = Join-Path $DestDir "manifest.json"
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $manifestPath -Encoding utf8
    Write-Host ""
    Write-Host "Manifest written: $manifestPath"
}

Write-Host ""
Write-Host "Summary: $($results.Count) packages | $($manifest.verified) verified | $failed failed"

if ($failed -gt 0) {
    Write-Error "$failed package(s) failed download or hash verification. Review output above."
    exit 2
}

Write-Host "Wheelhouse build complete."
