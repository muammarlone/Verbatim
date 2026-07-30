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

## STS-105/106 manifest-preview hardening

| Scenario | Expected | Observed | Result |
|---|---|---|---|
| Default state | Manifest/archive/Zoom paths stay off | Session reports all three off; reserved archive/Zoom flags fail startup if forced | pass |
| Valid CSV/XLSX | Equivalent plans from the strict schema | Synthetic CSV, UTF-8 BOM CSV, and XLSX normalize identically | pass |
| Hostile workbook | Active/hidden/external/ambiguous content fails before acquisition | Formula, external relationship, hidden row, merge, extra sheet, numeric cell, defined name, ZIP symlink, path, size, and schema cases return stable reasons | pass |
| Credential reference | API/audit/disk omit prompt or Windows target | API returns provider category only; canary absent from persisted files and audit | pass |
| Preview lifecycle | Plan remains bounded and non-durable | UUID memory plan, 30-minute maximum, capacity gate, expiry/restart loss; no job created | pass |
| Request budgets | Pre-parser and parser enforce 5 MiB maximum | Both layers return `MANIFEST_REQUEST_TOO_LARGE`; configuration can only lower the cap | pass |
| Near-limit parser | Complete under two seconds | 4.5 MB synthetic XLSX test call completed in 0.25 seconds including fixture handling | pass for this host/parser only |
| Dependency advisory | Direct runtime pins have no known advisory | Six findings on multipart 0.0.20; raised to 0.0.31; isolated 87-test overlay passed; narrowed direct audit returned none | pass with transitive-audit condition |
| Existing workflows | Upload and folder batch remain unchanged | Full 87-test regression and 84% branch coverage passed | pass |
| UI/accessibility | No premature operator-readiness claim | No manifest UI exists; browser/accessibility UAT remains STS-113 | deferred by scope |

Defects fixed in this increment: missing isolated-test parent setup, unsafe workbook-level defined names, ZIP symlink acceptance, portable Windows path gaps, and the vulnerable multipart pin. The global Python installation has unrelated dependency conflicts, and the full requirements audit cannot resolve `openai-whisper` build metadata; IT owns a clean wheelhouse/transitive qualification before pilot. Evidence is in `evidence/manifest-preview/`.

## STS-115 grounded product communication

| Scenario | Expected | Observed | Result |
|---|---|---|---|
| Capability truth | Working, contract-only, unavailable, and unsupported features remain distinct | Manual, capability matrix, narration, and cards preserve the boundaries | pass |
| Video provenance | Final and source recordings are integrity-addressed | Final SHA-256 and both retained source SHA-256 values match the evidence manifest | pass |
| Media usability | Explainer has reviewable video and narration | 1440x900 H.264 video, mono 48 kHz AAC audio, 10 scenes, 257.325 seconds | pass |
| Documentation navigation | Local Markdown links resolve | Deterministic link validation passed for the manual, capability matrix, explainer packet, and root README | pass |
| Evidence drift | Current metrics and claims fail closed when inconsistent | Regression validates 88 tests, 84% branch-inclusive coverage, 22 architecture gates, hashes, media streams, and claim boundaries | pass for this revision only |
| Broad quality claim | No unsupported 100% or production-readiness statement | Architect assessment retains open P1 gates and `proceed_with_conditions` | pass |

Visual review used the generated poster and contact sheet. The explainer is controlled synthetic evidence; representative-domain accuracy, accessibility, penetration, deployment, and connector qualification remain open.
