[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory,
    [string]$OutputFile = "evidence\batch-demo\verbatim-batch-end-to-end-demo.mp4"
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$resolvedRun = (Resolve-Path -LiteralPath $RunDirectory).Path
$reportPath = Join-Path $resolvedRun 'condensed-report.json'
$visualPath = Join-Path $resolvedRun 'verbatim-batch-demo-condensed.mp4'
if (-not (Test-Path -LiteralPath $reportPath)) { throw "Missing condensed report: $reportPath" }
if (-not (Test-Path -LiteralPath $visualPath)) { throw "Missing condensed visual: $visualPath" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw 'FFmpeg is required.' }

$report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
$narrationDir = Join-Path $resolvedRun 'narration'
New-Item -ItemType Directory -Path $narrationDir -Force | Out-Null
$segments = @(
    @{ Key = 'page_ready'; Offset = 0.3; Text = 'Verbatim now supports bounded folder-to-folder transcription inside one approved local workspace.' },
    @{ Key = 'batch_mode_opened'; Offset = 0.2; Text = 'The operator chooses relative input and output folders. The service cannot browse outside the configured workspace root.' },
    @{ Key = 'folders_configured'; Offset = 0.2; Text = 'This synthetic demonstration selects all five formats: plain text, Markdown, S R T, V T T, and JSON evidence.' },
    @{ Key = 'consent_confirmed'; Offset = 0.2; Text = 'One explicit authorization applies to every M P 4 directly inside the selected input folder.' },
    @{ Key = 'batch_started'; Offset = 0.6; Text = 'Two files enter the same bounded local validation and Whisper pipeline. Processing remains sequential and failures stay isolated per file.' },
    @{ Key = 'batch_complete'; Offset = 0.8; Text = 'Both transcripts are complete. Ten selected text outputs and a provenance manifest were written without replacing existing files.' },
    @{ Key = 'job_reviewed'; Offset = 0.5; Text = 'Each generated transcript remains reviewable beside its source recording and deterministic analysis.' },
    @{ Key = 'cleanup_opened'; Offset = 0.2; Text = 'Managed copies can be removed explicitly. Original input files and operator-requested output files remain untouched.' },
    @{ Key = 'cleanup_complete'; Offset = 0.4; Text = 'The batch record and managed jobs are deleted. The controlled synthetic folder-to-folder demonstration is complete.' }
)

Add-Type -AssemblyName System.Speech
$synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synthesizer.Rate = -1
$synthesizer.Volume = 100
$inputArguments = @()
$filterParts = @()
$mixLabels = @()
$index = 1
try {
    foreach ($segment in $segments) {
        $wavPath = Join-Path $narrationDir ("segment-{0:D2}.wav" -f $index)
        $synthesizer.SetOutputToWaveFile($wavPath)
        $synthesizer.Speak([string]$segment.Text)
        $synthesizer.SetOutputToNull()
        $inputArguments += @('-i', $wavPath)
        $baseTime = [double]$report.milestones.($segment.Key)
        $delay = [int][Math]::Round(($baseTime + [double]$segment.Offset) * 1000)
        $filterParts += "[$index`:a]adelay=$delay|$delay[a$index]"
        $mixLabels += "[a$index]"
        $index++
    }
} finally {
    $synthesizer.Dispose()
}

$narrationCount = $segments.Count
$filterParts += ((-join $mixLabels) + "amix=inputs=$narrationCount`:duration=longest`:normalize=0,loudnorm=I=-16`:TP=-1.5`:LRA=11[aout]")
$filterParts += '[0:v]tpad=stop_mode=clone:stop_duration=10[vout]'
$filterGraph = $filterParts -join ';'
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputFile))
New-Item -ItemType Directory -Path (Split-Path -Parent $resolvedOutput) -Force | Out-Null
$ffmpegArguments = @('-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', $visualPath)
$ffmpegArguments += $inputArguments
$ffmpegArguments += @(
    '-filter_complex', $filterGraph,
    '-map', '[vout]', '-map', '[aout]',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest',
    $resolvedOutput
)
& ffmpeg @ffmpegArguments
if ($LASTEXITCODE -ne 0) { throw "FFmpeg failed with exit code $LASTEXITCODE" }
Write-Output $resolvedOutput
