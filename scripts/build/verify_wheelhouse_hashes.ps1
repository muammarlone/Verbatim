<#
.SYNOPSIS
    Verify all files in the wheelhouse against recorded SHA-256 hashes.

.DESCRIPTION
    Reads dist/wheelhouse/manifest.json and re-hashes every file.
    Exits non-zero if any hash fails. Used before install to confirm
    the wheelhouse has not been tampered with.

.PARAMETER WheelhouseDir
    Wheelhouse directory. Default: dist/wheelhouse relative to repo root.

.NOTES
    Story:    STS-110, STS-117
    Gate:     QG-02
#>

param(
    [string]$WheelhouseDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..") | Select-Object -ExpandProperty Path
$DestDir = if ($WheelhouseDir) { $WheelhouseDir } else { Join-Path $RepoRoot "dist\wheelhouse" }
$ManifestPath = Join-Path $DestDir "manifest.json"

if (-not (Test-Path $ManifestPath)) {
    Write-Error "Manifest not found: $ManifestPath. Run build_offline_wheelhouse.ps1 first."
    exit 1
}

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$failed = 0
$verified = 0
$skipped = 0

Write-Host "Verifying wheelhouse: $DestDir"
Write-Host ""

foreach ($pkg in $manifest.packages) {
    if (-not $pkg.File) {
        $skipped++
        continue
    }
    if (-not $pkg.ExpectedSha256) {
        Write-Warning "  SKIP (no expected hash): $($pkg.Package)"
        $skipped++
        continue
    }

    $filePath = Join-Path $DestDir $pkg.File
    if (-not (Test-Path $filePath)) {
        Write-Warning "  MISSING: $($pkg.File)"
        $failed++
        continue
    }

    $actual = (Get-FileHash $filePath -Algorithm SHA256).Hash.ToLower()
    $expected = $pkg.ExpectedSha256.ToLower()

    if ($actual -eq $expected) {
        Write-Host "  [OK] $($pkg.Package)"
        $verified++
    } else {
        Write-Warning "  [FAIL] $($pkg.Package)"
        Write-Warning "         expected: $expected"
        Write-Warning "         actual:   $actual"
        $failed++
    }
}

Write-Host ""
Write-Host "Summary: $verified verified | $failed failed | $skipped skipped"

if ($failed -gt 0) {
    Write-Error "$failed file(s) failed hash verification. Do NOT use this wheelhouse for installation."
    exit 2
}

Write-Host "All hashes verified. Wheelhouse is intact."
