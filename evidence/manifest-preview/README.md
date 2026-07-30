# STS-105/106 Manifest-Preview Evidence

Recorded July 29, 2026 on Windows with Python 3.13.0 using synthetic data only.

## Reproduction

```powershell
python scripts\validate_architecture.py
python -m pytest
python -m pytest --cov=secure_transcribe --cov-branch --cov-report=term-missing
python -m pytest tests\test_manifest.py::test_near_limit_xlsx_preview_parser_stays_within_performance_budget -vv --durations=3
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
node --check src\secure_transcribe\static\app.js
python -m build --wheel
python -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off
```

## Results and boundaries

- 21/21 deterministic architecture gates and 87/87 tests passed.
- Measured branch coverage was 84% overall and 84% for `manifest.py`.
- The near-limit synthetic XLSX test call completed in 0.25 seconds, including fixture handling, below the two-second parser threshold on this host.
- The API preview is mutation-token protected, disabled by default, creates no jobs, persists no upload or credential target, and writes metadata-only audit.
- The original `python-multipart==0.0.20` pin produced six direct advisory findings. Version 0.0.31 passed all 87 tests in an isolated system-site overlay and the narrowed direct-pin audit returned no known vulnerabilities.
- A normal full-requirements audit is not evidence-complete: the audit tool cannot resolve the pinned `openai-whisper` build metadata because its temporary build environment lacks `pkg_resources`. The shared global Python also contains unrelated dependency conflicts. A clean approved wheelhouse/SBOM/transitive audit remains an IT gate.
- No manifest UI, accessibility UAT, plan execution, archive extraction, credential provider, Zoom connector, installer, Docker, or Codespaces path is claimed by this increment.

Machine-readable results are in `manifest-preview-evidence.json`. Synthetic parser fixtures are generated in memory by `tests/test_manifest.py`; no recording, password, token, or corporate data is included.
