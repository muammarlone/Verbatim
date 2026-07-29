# Folder-to-Folder Batch Demonstration

The primary deliverable is [verbatim-batch-end-to-end-demo.mp4](verbatim-batch-end-to-end-demo.mp4), a 62.2-second narrated recording of the controlled multi-file workflow.

## Demonstrated path

1. Open the folder-batch mode.
2. Choose relative input and output folders inside the configured workspace root.
3. Select TXT, Markdown, SRT, VTT, and JSON outputs.
4. Confirm authority for every directly contained MP4.
5. Process two synthetic MP4s through real local FFmpeg and Whisper.
6. Review the batch manifest, per-file outputs, and one transcript.
7. Remove managed jobs and batch metadata while preserving the original input and requested output files.

## Verification record

- Run ID: `20260729T232553Z`
- Input files: 2 synthetic, non-sensitive MP4s
- Output files: 10 selected text/caption/evidence files plus 1 manifest
- Formats: TXT, Markdown, SRT, VTT, JSON
- Exact fixture matches: 2 of 2 JSON transcripts
- Recorded batch-processing wall time: 39.095 seconds
- Editing: only the middle of the processing wait is played at 16× with a visible label
- Browser console errors: 0
- Managed job entries after cleanup: 0
- Managed batch entries after cleanup: 0
- Final video: 1440×900 H.264, 25 fps, mono AAC, 62.2 seconds
- Final SHA-256: `1e2907c7d736b9306f732954c4cf4ffee83c0e68d0ee7956fc0344d25624b5f4`

The raw capture, condensed visual, narration clips, timing reports, synthetic inputs, generated outputs, audit events, and server log are retained under `runs/20260729T232553Z/`.

## Reproduce

```powershell
python scripts\record_batch_demo.py
python scripts\condense_batch_demo.py evidence\batch-demo\runs\<run-id>
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_batch_demo_narration.ps1 -RunDirectory evidence\batch-demo\runs\<run-id>
```

## Claim boundary

This demonstrates one controlled two-file synthetic batch. It does not establish general accuracy, throughput on other hardware, production security, accessibility, compliance, corporate deployment approval, or user value.
