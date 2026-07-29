[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory,
    [string]$ReportName = "condensed-report.json",
    [string]$VisualName = "verbatim-demo-condensed.mp4",
    [string]$OutputFile = "evidence\demo\verbatim-end-to-end-demo.mp4"
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$resolvedRun = (Resolve-Path -LiteralPath $RunDirectory).Path
$reportPath = Join-Path $resolvedRun $ReportName
$visualPath = Join-Path $resolvedRun $VisualName
if (-not (Test-Path -LiteralPath $reportPath)) { throw "Missing recording report: $reportPath" }
if (-not (Test-Path -LiteralPath $visualPath)) { throw "Missing visual recording: $visualPath" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw 'FFmpeg is required.' }

$report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
$narrationDir = Join-Path $resolvedRun 'narration'
New-Item -ItemType Directory -Path $narrationDir -Force | Out-Null

$segments = @(
    @{ Key = 'page_ready'; Offset = 0.4; Text = 'Meet Verbatim, a local-first transcription workspace for managed corporate endpoints.' },
    @{ Key = 'file_selected'; Offset = 0.2; Text = 'This demonstration uses synthetic, non-sensitive audio. The media, model, and job data stay on this device.' },
    @{ Key = 'processing_started'; Offset = 0.4; Text = 'After authorization is confirmed, Verbatim validates the MP4, extracts its audio, and runs Whisper in a killable, time-bounded local worker.' },
    @{ Key = 'job_complete'; Offset = 0.8; Text = 'The completed review links each transcript segment back to the source video.' },
    @{ Key = 'search_shown'; Offset = 0.3; Text = 'Search narrows the transcript instantly, while the source remains one click away.' },
    @{ Key = 'analysis_actions'; Offset = 0.2; Text = 'Deterministic analysis surfaces key moments, action candidates, questions, and recurring terms for human review.' },
    @{ Key = 'export_saved'; Offset = 0.2; Text = 'Exports include text, captions, review notes, and a provenance-rich JSON evidence package.' },
    @{ Key = 'health_opened'; Offset = 0.2; Text = 'The readiness panel confirms local media tools, model availability, and zero network requirement.' },
    @{ Key = 'delete_opened'; Offset = 0.2; Text = 'Deletion is explicit and removes the synthetic source and its derived artifacts.' },
    @{ Key = 'deleted'; Offset = 0.4; Text = 'The end-to-end demonstration is complete. Pilot use remains subject to the documented security and records-management conditions.' }
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
$outputDirectory = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

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
