[CmdletBinding()]
param(
    [string]$OutputDirectory = "evidence\explainer\build\narration"
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null

$segments = @(
    'Verbatim is a local-first Windows utility for turning authorized recordings — M P 4, M 4 A, M P 3, W A V, and other approved formats — into reviewable text. Media processing and the Whisper model stay on this device. This explainer uses synthetic evidence and separates working features from planned ones.',
    'For one recording, choose a media file — M P 4, M 4 A, M P 3, W A V, or another supported format — select a language, confirm authority, and start local transcription. Verbatim validates the file format and audio, enforces size and duration budgets, extracts audio with F F mpeg, and runs Whisper in a killable, time-bounded worker. Each transcript segment receives a confidence indicator — high, medium, or low — based on Whisper log-probability and no-speech signals.',
    'The completed transcript links passages to the source video. Search and timestamp controls support human verification. Rule-based review aids surface moments, action keywords, questions, terms, counts, and pace. They are cues, not judgment. Exports include plain text, Markdown, subtitles, web captions, and a provenance-rich J S O N package.',
    'Folder mode processes up to twenty-five media files — M P 4, M 4 A, M P 3, W A V, and others — directly inside one approved workspace. The operator chooses relative input and output folders and the required formats. Scanning is non-recursive, existing outputs are never overwritten, and one failed file does not erase successful results from the rest of the batch.',
    'Deletion is explicit. A single-job deletion removes Verbatim''s managed source and derived files. Batch cleanup removes managed copies and metadata but preserves original inputs and requested output files. Downloads, backups, and other external copies remain under the destination''s records policy.',
    'Password-protected archive extraction, Microsoft Teams retrieval, and Zoom Cloud retrieval are not available today. The platform connector architecture is defined in A D R zero zero six — Teams as Phase 3 A and Zoom as Phase 3 B — but neither is implemented. The current manifest feature is a disabled backend preview contract. It validates and redacts bounded C S V or Excel rows in memory, but it does not resolve credentials, contact external platforms, unlock an archive, or start a job. Signed installation and production deployment qualification also remain open.',
    'The product''s strengths are data locality, reviewable timestamps, deterministic budgets, bounded failures, portable outputs, and explicit evidence. The implementation avoids silent downloads, cloud transcription, path traversal, output overwrite, and unbounded local workers.',
    'The trade-offs are real. Local transcription uses endpoint C P U and storage. Accuracy depends on language, noise, speakers, and vocabulary. Anyone with the same operating system access may read local files unless I T applies stronger controls. Rule-based analysis can miss context, and exports leave the managed deletion boundary.',
    'Before use, verify authority, system readiness, approved storage, and available capacity. Review consequential text against the recording. Export only to approved locations, then apply the organization''s retention and deletion rules to every copy.',
    'Current evidence includes one hundred thirty-eight passing tests, eighty-three percent Python branch coverage, twenty-three deterministic architecture gates, four responsive browser quality cases, exact controlled synthetic fixtures, and two recorded workflows. The principal architect roadmap correctly blocks pilot promotion on six open gates. These results support a controlled demonstration, not a general quality, compliance, security, accessibility, or accuracy claim. The next gates are representative domain evaluation, manual accessibility and penetration testing, signed deployment, endpoint isolation, records approval, and environment qualification.'
)

Add-Type -AssemblyName System.Speech
$synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synthesizer.Rate = -1
$synthesizer.Volume = 100
$voice = $synthesizer.Voice.Name
$records = @()

try {
    for ($index = 0; $index -lt $segments.Count; $index++) {
        $path = Join-Path $resolvedOutput ("scene-{0:D2}.wav" -f ($index + 1))
        $synthesizer.SetOutputToWaveFile($path)
        $synthesizer.Speak($segments[$index])
        $synthesizer.SetOutputToNull()
        $records += [ordered]@{
            scene = $index + 1
            text = $segments[$index]
            file = $path.Substring($projectRoot.Length).TrimStart([char]'\')
        }
    }
} finally {
    $synthesizer.Dispose()
}

$manifest = [ordered]@{
    schema_version = '1.0'
    generated_at = [DateTimeOffset]::UtcNow.ToString('o')
    engine = 'Windows System.Speech'
    voice = $voice
    rate = -1
    segments = $records
}
$manifestPath = Join-Path $resolvedOutput 'narration-manifest.json'
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Output $manifestPath
