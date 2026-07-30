# Verbatim User Manual

Verbatim Secure Transcription Studio turns authorized MP4 recordings into local,
reviewable transcripts. It is designed for one operator on a managed Windows endpoint.
The browser interface binds to the local machine, the Whisper model runs on the device,
and the application does not call a cloud transcription service.

This manual describes version 0.2.0. It separates working features from foundations that
remain disabled or incomplete. Read [Features and limitations](FEATURES_AND_LIMITATIONS.md)
before using Verbatim with corporate recordings.

## Before you begin

You need:

- Windows with Python 3.11 or newer.
- An IT-approved FFmpeg and FFprobe installation on `PATH`.
- An approved Whisper `.pt` model stored locally.
- A local data directory whose access-control list is limited to the operator or service account.
- Permission to process every recording you select.
- For folder batches, an IT-approved batch workspace with enough free disk space.

Verbatim does not download a model. If FFmpeg, FFprobe, or the model is missing, the UI
shows **Needs attention** and keeps transcription controls disabled.

## Start Verbatim

1. Open PowerShell in the project directory.
2. Create the local environment and install the pinned packages.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Set approved local paths for this session.

   ```powershell
   $env:STS_MODEL_PATH = "C:\approved\models\base.pt"
   $env:STS_DATA_DIR = "C:\approved\VerbatimData"
   $env:STS_BATCH_ROOT = "C:\approved\VerbatimBatchWorkspace"
   ```

4. Start the utility.

   ```powershell
   .\Start-Verbatim.ps1
   ```

5. Open `http://127.0.0.1:8765` if the browser does not open automatically. Select
   **System ready** and confirm that FFmpeg, the local model, and external-network status
   are all ready.

If package installation must happen without internet access, IT should prepare and scan an
approved wheelhouse on a connected build machine. Install it with the constrained command
in the project [README](../README.md#quick-start).

## Transcribe one MP4

1. In **Single MP4** mode, select or drop an `.mp4` file.
2. Choose **Detect automatically** or a supported two-letter language choice.
3. Confirm that you are authorized to process the recording.
4. Select **Transcribe locally**.
5. Keep the utility running while Verbatim validates the file, extracts mono audio, runs
   local Whisper, and prepares deterministic review aids.

The review page appears when processing completes. A stopped job shows a stable reason
code and a plain-language message. Fix the stated condition and create a new job; failed
jobs are not silently retried.

## Transcribe a folder to a folder

Folder batches process MP4 files directly inside one approved input folder. Scanning is
non-recursive: MP4s inside nested folders are ignored.

1. Place the source MP4s in a folder under `STS_BATCH_ROOT`.
2. Create a separate output folder under the same root.
3. In Verbatim, choose **Folder batch**.
4. Enter the input and output paths relative to the displayed workspace root. For example,
   use `incoming` and `transcripts`, not absolute Windows paths.
5. Select one or more outputs: TXT, Markdown, SRT, VTT, or JSON.
6. Confirm authority for every MP4 directly inside the input folder.
7. Select **Transcribe folder locally**.

The batch card reports each file separately. One bad file does not erase successful results
from other files. Verbatim refuses nested traversal, links or junctions, the same input and
output folder, more than 25 files, more than the configured byte budget, and any output
name that already exists.

## Review a transcript

- Select a completed recording from **Recent recordings**.
- Select a transcript passage to seek the local video to that timestamp.
- Enter text in **Search transcript** to narrow the visible passages.
- Use **Key moments**, **Actions**, **Questions**, and **Terms** to review deterministic
  cues. These are rule-based aids, not conclusions or professional judgment.
- Open **How this analysis works** for the method limitations.

Transcripts can be wrong, especially with noise, overlapping speakers, accents, specialized
terms, or weak source audio. Verify consequential statements against the linked recording.

## Export results

Select **Export** on a completed recording and choose:

| Format | Use |
|---|---|
| TXT | Plain transcript text |
| SRT | Timestamped subtitles for media tools |
| VTT | Web-compatible timed captions |
| Markdown | Human-readable review notes with analysis |
| JSON | Versioned transcript, analysis, model ID, and provenance evidence |

Single-recording exports are downloaded through the browser. Batch exports are written to
the approved output folder. Exported copies are outside Verbatim's deletion boundary and
must be governed by the destination's access, DLP, retention, and backup rules.

## Delete data

For a single completed or failed job, select the trash control and then **Delete
permanently**. Verbatim removes its managed MP4, working audio, transcript, analysis, and
job record. Running jobs cannot be deleted until they reach a terminal state.

For a batch, select **Remove managed copies**. This removes Verbatim's managed job copies,
derived records, and batch metadata. It intentionally preserves the original input files
and the requested text files already written to the output folder.

Neither action deletes separate browser downloads, manually copied exports, backups, or
indexed copies outside the configured data directory.

## Troubleshooting

| What you see | Meaning | What to do |
|---|---|---|
| **Needs attention** | FFmpeg, FFprobe, or the model is unavailable | Open the readiness dialog; correct the approved path or installation, then restart |
| `UNSUPPORTED_EXTENSION` or `UNSUPPORTED_MEDIA_TYPE` | The selected upload is not an accepted MP4 | Select an MP4 with the expected media type |
| `INVALID_MP4_SIGNATURE` | The file extension says MP4 but the file signature does not | Obtain a valid MP4; do not rename another format |
| `AUDIO_TRACK_MISSING` | The MP4 has no usable audio stream | Use a recording with an audio track |
| `MEDIA_TOO_LONG` | The recording exceeds the configured duration budget | Split it under the approved records process or ask IT to review the limit |
| `TRANSCRIPTION_TIMEOUT` | Local Whisper exceeded its elapsed-time budget | Preserve the reason code, verify capacity, and retry only after the cause is understood |
| `NO_MP4_FILES` | The batch input has no directly contained MP4 | Move approved MP4s into the selected folder; nested folders are not scanned |
| `BATCH_FILE_LIMIT_EXCEEDED` or `BATCH_SIZE_LIMIT_EXCEEDED` | File count or total bytes exceed a governed limit | Divide the work into smaller authorized batches |
| Output collision error | A requested output already exists | Choose an empty output folder or move the existing files; Verbatim never overwrites |
| The local service is unavailable | The launcher stopped or port 8765 is unavailable | Restart Verbatim and refresh the page |

Keep stable reason codes with support evidence. Do not include recording content, secrets,
or credential values in tickets or logs unless an approved support process explicitly
requires them.

## Administrator configuration

The main environment controls are listed in the project [README](../README.md#configuration).
Important governed ceilings are 2 GiB per upload by default, 25 MP4s per batch, 10 GiB per
batch, four hours of media, and seven-day startup retention. Configuration can lower the
manifest byte and lifetime limits but cannot enable archive or Zoom execution.

`STS_MANIFEST_INTAKE_ENABLED=true` exposes a backend-only contract-testing route. It does
not add a UI, retrieve Zoom media, unlock protected archives, or start transcription. Keep
it off outside an approved contract test.

## Safe operating checklist

Before each use:

- Confirm recording authority and the approved purpose.
- Confirm the readiness dialog reports local tools and model availability.
- Use synthetic or low-risk authorized material until pilot approval is complete.
- Verify disk space and the correct batch input/output folders.
- Review transcript meaning against the source before consequential use.
- Export only to an approved destination.
- Delete managed data and external copies according to the records policy.

For security assumptions, pilot gates, and residual risks, read
[SECURITY.md](../SECURITY.md), the [readiness report](../governance/READINESS_REPORT.md),
and the [risk register](../governance/RISK_REGISTER.md).
