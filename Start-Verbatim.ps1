[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Join-Path $projectRoot 'src'
$localPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (Test-Path -LiteralPath $localPython) {
    $pythonCommand = $localPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = 'python'
} else {
    throw 'Python 3.11 or newer is required. Ask IT to install the approved Python runtime.'
}

$env:PYTHONPATH = $sourceRoot
$arguments = @('-m', 'secure_transcribe', '--port', $Port)
if ($NoBrowser) {
    $arguments += '--no-browser'
}

Write-Host "Starting Verbatim on http://127.0.0.1:$Port"
Write-Host 'The service is restricted to this device.'
& $pythonCommand @arguments
