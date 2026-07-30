# Grounded Product Explainer

[verbatim-grounded-product-explainer.mp4](verbatim-grounded-product-explainer.mp4)
is a 269.102-second narrated overview of working capabilities, usage, strengths,
trade-offs, unavailable features, and release gates.

## Grounding

- Every product clip comes from the retained single-file or two-file synthetic demo.
- Slides identify synthetic evidence and a local-only demonstration.
- The manifest scene states that preview is backend-only and disabled by default.
- Protected archive extraction, Zoom retrieval, signed deployment, and production approval
  are explicitly described as unavailable or open.
- The final scene reports 138 tests (334 total at repo HEAD; 16 skipped on unfilled env placeholders), 83% measured Python branch coverage, 23 architecture
  gates, and six open pilot blockers without converting those measures into a general quality claim.

## Verification record

- Resolution: 1440 x 900
- Video: H.264 at 25 fps
- Audio: mono AAC at 48 kHz
- Scenes: 10
- Duration: 318.805 seconds
- SHA-256: `b13c390b560e88c2a26ff2ad9b7f23e2945a27cd33a5c0fc67f37eb6ae178d9b`
- Source single-file video SHA-256:
  `e0bbd3d1edc899ecbfced7d243d6560c24e2f6446bb68d7d39df5e938c240589`
- Source batch video SHA-256:
  `1e2907c7d736b9306f732954c4cf4ffee83c0e68d0ee7956fc0344d25624b5f4`

Machine-readable details are in [explainer-evidence.json](explainer-evidence.json).
The [poster](explainer-poster.png) and [contact sheet](explainer-contact-sheet.png) support
visual review. Narration, cards, and encoded scene intermediates are reproducible in the
ignored `build` folder.

## Reproduce

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_explainer_narration.ps1
python scripts\build_explainer_video.py
python scripts\validate_product_evidence.py
```

Requirements: the two retained source demonstrations, Python with Pillow, Windows SAPI,
FFmpeg, FFprobe, and the standard Segoe UI and Georgia fonts. The build does not call a
cloud service.

## Claim boundary

This is a synthetic, controlled explainer. It does not establish general transcription
accuracy, production security, accessibility, compliance, deployment approval, or ROI.
