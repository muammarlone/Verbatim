# Verbatim Grounded Product Explainer

Target length: about 4 to 5 minutes. All footage and claims use synthetic evidence retained in
this repository. Product clips are drawn from the verified single-file and folder-batch
recordings; their original accelerated wait disclosures remain documented in the source evidence.

## Scene 1: What Verbatim is

**Visual:** Branded title card with the current product screenshot.

**Narration:** Verbatim is a local-first Windows utility for turning authorized MP4
recordings into reviewable text. Media processing and the Whisper model stay on this device.
This explainer uses synthetic evidence and separates working features from planned ones.

## Scene 2: Single-recording workflow

**Visual:** Verified synthetic upload and local-processing footage.

**Narration:** For one recording, choose an MP4, select a language, confirm authority, and
start local transcription. Verbatim validates the file and audio, enforces size and duration
budgets, extracts audio with FFmpeg, and runs Whisper in a killable, time-bounded worker.

## Scene 3: Review, analysis, and export

**Visual:** Transcript search, linked playback, analysis tabs, and export menu.

**Narration:** The completed transcript links passages to the source video. Search and
timestamp controls support human verification. Rule-based review aids surface moments,
action keywords, questions, terms, counts, and pace. They are cues, not judgment. Exports
include TXT, Markdown, SRT, VTT, and a provenance-rich JSON package.

## Scene 4: Folder-to-folder processing

**Visual:** Verified two-file folder batch footage.

**Narration:** Folder mode processes up to twenty-five MP4s directly inside one approved
workspace. The operator chooses relative input and output folders and the required formats.
Scanning is non-recursive, existing outputs are never overwritten, and one failed file does
not erase successful results from the rest of the batch.

## Scene 5: Cleanup boundary

**Visual:** Single delete and managed-batch cleanup dialogs.

**Narration:** Deletion is explicit. A single-job deletion removes Verbatim's managed source
and derived files. Batch cleanup removes managed copies and metadata but preserves original
inputs and requested output files. Downloads, backups, and other external copies remain under
the destination's records policy.

## Scene 6: What is not available

**Visual:** Capability boundary card.

**Narration:** Password-protected archive extraction and Zoom retrieval are not available.
The current manifest feature is a disabled backend preview contract. It validates and redacts
bounded CSV or XLSX rows in memory, but it does not resolve credentials, contact Zoom, unlock
an archive, or start a job. Signed installation and production deployment qualification also
remain open.

## Scene 7: Strengths

**Visual:** Strengths card with local, bounded, reviewable, and portable pillars.

**Narration:** The product's strengths are data locality, reviewable timestamps, deterministic
budgets, bounded failures, portable outputs, and explicit evidence. The implementation avoids
silent downloads, cloud transcription, path traversal, output overwrite, and unbounded local workers.

## Scene 8: Trade-offs

**Visual:** Trade-offs card.

**Narration:** The trade-offs are real. Local transcription uses endpoint CPU and storage.
Accuracy depends on language, noise, speakers, and vocabulary. Anyone with the same operating
system access may read local files unless IT applies stronger controls. Rule-based analysis can
miss context, and exports leave the managed deletion boundary.

## Scene 9: How to use it safely

**Visual:** Five-step operating checklist.

**Narration:** Before use, verify authority, system readiness, approved storage, and available
capacity. Review consequential text against the recording. Export only to approved locations,
then apply the organization's retention and deletion rules to every copy.

## Scene 10: Evidence and next gates

**Visual:** Evidence card with current measured results and open gates.

**Narration:** Current evidence includes eighty-eight passing tests, eighty-four percent Python
branch coverage, twenty-two architecture gates, browser checks, exact controlled synthetic
fixtures, and two recorded workflows. These results support a controlled demonstration, not a
general quality, compliance, security, accessibility, or accuracy claim. The next gates are
representative domain evaluation, accessibility and penetration testing, signed deployment,
and approved connector security.
