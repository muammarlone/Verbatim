# Recorded End-to-End Demonstration

The primary deliverable is [verbatim-end-to-end-demo.mp4](verbatim-end-to-end-demo.mp4), a 114.52-second narrated recording of the complete controlled workflow.

## Demonstrated path

1. Select the synthetic, non-sensitive MP4 fixture.
2. Confirm recording authorization.
3. Run real FFprobe, FFmpeg, and local Whisper processing.
4. Review and search the time-linked transcript.
5. Inspect deterministic action, question, term, and key-moment analysis.
6. Download the JSON evidence package.
7. Review local system readiness.
8. Permanently delete the job and its stored artifacts.

## Verification record

- Run ID: `20260729T224021Z`
- Fixture duration: 9.193016 seconds
- Recorded local processing wall time: 80.618 seconds while screen capture and Whisper shared the CPU
- Editing: only the middle of the processing wait is played at 12×; the video labels this interval on-screen
- Browser console errors: 0
- Exported transcript: exact match to the intended 17-word synthetic fixture
- Analysis method: `deterministic-extractive-v1`
- Audit sequence: `application_started`, `job_created`, `job_completed`, `job_deleted`
- Final video: 1440×900 H.264, 25 fps, mono AAC, 114.52 seconds
- Final SHA-256: `e0bbd3d1edc899ecbfced7d243d6560c24e2f6446bb68d7d39df5e938c240589`

Machine-readable details are in [demo-evidence.json](demo-evidence.json). The raw visual capture, condensed visual, exported JSON, audit events, narration segments, and timing reports are retained under `runs/20260729T224021Z/`.

## Reproduce

```powershell
python scripts\record_demo.py
python scripts\condense_demo.py evidence\demo\runs\<run-id>
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_demo_narration.ps1 -RunDirectory evidence\demo\runs\<run-id>
```

The scripts require a locally provisioned Whisper model, FFmpeg, Playwright Chromium, and Windows SAPI. They do not download a model or call a cloud transcription API.

## Claim boundary

This recording demonstrates one controlled synthetic workflow. It does not establish general transcription accuracy, production security, accessibility, compliance, corporate deployment approval, processing speed on other hardware, or user value.
