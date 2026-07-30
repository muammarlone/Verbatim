#!/usr/bin/env bash
set -euo pipefail

echo "=== Verbatim Codespaces dev setup ==="

# Stop gate: verify this is a Codespaces/devcontainer environment
if [ "${VERBATIM_CODESPACES_ENV:-}" != "true" ]; then
  echo "ERROR: VERBATIM_CODESPACES_ENV is not set. This script must run inside the devcontainer." >&2
  exit 1
fi

# Install Python dependencies (offline wheel cache preferred if present)
pip install --quiet -r requirements.txt

# Install test dependencies
pip install --quiet pytest pytest-cov pytest-asyncio httpx faker pillow

# Create synthetic-only data directories
mkdir -p data/codespaces-dev/jobs data/codespaces-dev/audit data/codespaces-dev/batches
mkdir -p data/codespaces-dev/batch-workspace/input data/codespaces-dev/batch-workspace/output

# Write a clearly-labelled fake model stub (zero-byte .pt) so the health check
# can confirm model_ready=false without loading real weights
touch data/fake-model.pt
echo "  fake Whisper stub at data/fake-model.pt (model_ready will be false)"

# Verify no production credentials are reachable from this environment
if compgen -G "/mnt/onedrive/**/*.mp4" > /dev/null 2>&1; then
  echo "ERROR: Corporate OneDrive recordings are mounted. See .devcontainer/STOP_GATE.md." >&2
  exit 1
fi

echo ""
echo "=== STOP GATE: Read .devcontainer/STOP_GATE.md before running Verbatim here. ==="
echo ""
cat .devcontainer/STOP_GATE.md
echo ""
echo "Setup complete. Run: python -m pytest"
