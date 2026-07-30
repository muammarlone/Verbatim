# UAT Report — 2026-07-29

## Environment

- Windows; Python 3.13.0
- FFmpeg/FFprobe 7.1
- `openai-whisper==20240930`
- Local model: `base.pt`, SHA-256 `ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e`
- Synthetic, non-sensitive 9.193-second MP4

## Results

| Scenario | Expected | Observed | Result |
|---|---|---|---|
| Upload authorized MP4 | Job accepted and bounded | HTTP 202, local job created | pass |
| Real media processing | Complete inside 180-second budget | Complete in 16.18 seconds | pass |
| Transcript | Time-linked intended speech | Exact intended 17 words, 2 segments | pass for this fixture only |
| Provenance | Model artifact uniquely identified | Full SHA-256 in job/transcript/export | pass |
| Export | JSON evidence available | HTTP 200 | pass |
| Media review | Browser streams local MP4 | Inline content disposition | pass |
| Responsive UI | No overflow/console error at three widths | 375/768/1440 px passed | pass |
| Completed-state visibility | Only completed review panels visible | Processing/failure hidden; transcript and analysis visible | pass after defect fix |
| Recorded end-to-end workflow | Consent through deletion is reviewable | 114.52-second narrated MP4; export saved; readiness shown; deletion recorded | pass for synthetic workflow |
| Recording integrity | Edits and errors are disclosed | 0 console errors; measured processing 80.618 seconds; processing wait visibly played at 12× | pass |
| Real two-file batch | Two MP4s complete independently and write selected formats | Complete in 25.34 seconds; 2 exact fixture matches; TXT/MD/JSON plus manifest written | pass for synthetic fixtures |
| All batch formats | TXT, Markdown, SRT, VTT, and JSON are produced per file | 10 selected outputs plus 1 manifest in recorded run | pass |
| Batch filesystem controls | Stay inside root and preserve existing outputs | Traversal and missing consent rejected; existing file returned `OUTPUT_EXISTS` unchanged | pass |
| Per-file isolation | One unacceptable file does not conceal valid work | Empty MP4 rejected; valid MP4 completed; batch status `partial` | pass |
| Batch responsive UI | No overflow/console error at desktop, tablet, and mobile | Dedicated 375 px check had zero overflow; console errors 0 | pass |
| Batch cleanup | Managed copies removed without deleting input/output folders | 0 managed jobs and 0 batch records; 11 requested output/manifest files remained | pass |
| L1-L3 architecture validation | Definitions, implementation map, tests, and rendered diagrams agree | 19/19 deterministic gates passed; forbidden-import and dependency-edge negative controls blocked as expected | pass for this revision only |
| Recorded batch workflow | Folder selection through review and cleanup is inspectable | 62.2-second narrated MP4; measured wait 39.095 seconds; visible 16× label | pass for synthetic workflow |

Screenshots are in `evidence/screenshots/` and `evidence/batch-demo/`; both recording packets include machine-readable evidence. Test data is synthetic and does not establish performance on real corporate recordings.
