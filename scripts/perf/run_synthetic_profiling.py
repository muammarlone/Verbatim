"""Synthetic performance profiling for QG-06.

Profiles synthetic workloads using mock transcription to capture P50/P95
wall-clock times, peak CPU, and peak RSS by file-size bracket.

Writes results to evidence/capacity/docker-profiling-{date}.json with an
explicit 'not_qualified_endpoint: true' marker. Real managed-endpoint
profiling is a human gate (QG-06 exit criterion).

Usage:
    python scripts/perf/run_synthetic_profiling.py \\
        --fixtures-dir tests/fixtures \\
        --output-dir evidence/capacity \\
        --mock          # use mock transcriber (default; safe for CI)

    # Live mode (requires Whisper model and FFmpeg on path):
    python scripts/perf/run_synthetic_profiling.py \\
        --fixtures-dir tests/fixtures \\
        --output-dir evidence/capacity \\
        --live

Guard: live mode requires VERBATIM_PERF_LIVE=1 environment variable so
profiling is never silently run in production with real data.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Bracket classification
# ---------------------------------------------------------------------------

_SIZE_BRACKETS = {
    "small": (0, 10),       # 0–10 MB
    "medium": (10, 50),     # 10–50 MB
    "large": (50, 200),     # 50–200 MB
}


def _classify_size(size_mb: float) -> str:
    for label, (lo, hi) in _SIZE_BRACKETS.items():
        if lo <= size_mb < hi:
            return label
    return "large"


# ---------------------------------------------------------------------------
# Mock transcriber — deterministic latency model
# ---------------------------------------------------------------------------

def _mock_process(size_mb: float, seed: int = 0) -> dict[str, float]:
    """Return synthetic timing metrics for a file of given size."""
    rng = random.Random(seed)
    # Simulate ~5 s/MB baseline with ±20% jitter (realistic Whisper-base rate)
    base_seconds = size_mb * 5.0
    elapsed = base_seconds * rng.uniform(0.8, 1.2)
    cpu_pct = rng.uniform(75.0, 95.0)
    rss_mb = 450.0 + size_mb * 0.5 + rng.uniform(-20, 20)
    temp_mb = size_mb * 1.1
    return {
        "elapsed_seconds": round(elapsed, 2),
        "peak_cpu_pct": round(cpu_pct, 1),
        "peak_rss_mb": round(rss_mb, 1),
        "temp_storage_mb": round(temp_mb, 2),
        "failed": False,
    }


# ---------------------------------------------------------------------------
# Core profiling loop
# ---------------------------------------------------------------------------

def _collect_scenarios(protocol: dict[str, Any], mock: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for sc in protocol.get("scenarios", []):
        sc_id = sc["id"]
        size_mb: float = sc["size_mb"]
        bracket = _classify_size(size_mb)

        if sc.get("requires_human"):
            results.append({
                "scenario_id": sc_id,
                "bracket": bracket,
                "size_mb": size_mb,
                "status": "PENDING_HUMAN",
                "note": sc.get("human_note", ""),
            })
            continue

        if not mock and os.getenv("VERBATIM_PERF_LIVE") != "1":
            print(
                f"ERROR: live mode requires VERBATIM_PERF_LIVE=1 env var. "
                f"Pass --mock for CI-safe run.",
                file=sys.stderr,
            )
            sys.exit(2)

        repetitions = sc.get("repetitions", 3)
        timings: list[float] = []
        cpu_peaks: list[float] = []
        rss_peaks: list[float] = []
        temp_peaks: list[float] = []
        failures = 0

        for rep in range(repetitions):
            if mock:
                m = _mock_process(size_mb, seed=hash(sc_id + str(rep)) & 0xFFFF)
            else:
                # Live mode: delegate to actual service pipeline
                m = _live_process(size_mb, sc)

            if m["failed"]:
                failures += 1
            else:
                timings.append(m["elapsed_seconds"])
                cpu_peaks.append(m["peak_cpu_pct"])
                rss_peaks.append(m["peak_rss_mb"])
                temp_peaks.append(m["temp_storage_mb"])

        if timings:
            sorted_t = sorted(timings)
            n = len(sorted_t)
            p50 = statistics.median(sorted_t)
            p95_idx = max(0, int(n * 0.95) - 1)
            p95 = sorted_t[p95_idx]
        else:
            p50 = p95 = None

        results.append({
            "scenario_id": sc_id,
            "bracket": bracket,
            "size_mb": size_mb,
            "repetitions": repetitions,
            "failures": failures,
            "p50_seconds": round(p50, 2) if p50 is not None else None,
            "p95_seconds": round(p95, 2) if p95 is not None else None,
            "peak_cpu_pct": round(max(cpu_peaks), 1) if cpu_peaks else None,
            "peak_rss_mb": round(max(rss_peaks), 1) if rss_peaks else None,
            "temp_storage_high_water_mb": round(max(temp_peaks), 2) if temp_peaks else None,
            "status": "OK" if p50 is not None else "ALL_FAILED",
        })

    return results


def _synth_wav(size_mb: float, dest: Path) -> None:
    """Write a synthetic WAV file of approximately *size_mb* MB."""
    import struct
    import wave

    # 16-bit mono 16 kHz silence — 2 bytes/sample
    sample_rate = 16000
    target_bytes = int(size_mb * 1024 * 1024)
    num_samples = target_bytes // 2

    with wave.open(str(dest), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)


def _poll_job(
    base_url: str, job_id: str, token: str, timeout: float = 1800.0
) -> tuple[str, float]:
    """Poll GET /api/jobs/{job_id} until terminal status. Returns (status, elapsed)."""
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        req = urllib.request.Request(f"{base_url}/api/jobs/{job_id}")
        req.add_header("X-Request-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Poll failed: {exc}") from exc
        status = data.get("status", "")
        if status in {"complete", "failed", "error"}:
            return status, time.monotonic()
        time.sleep(2.0)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


def _live_process(size_mb: float, sc: dict[str, Any]) -> dict[str, float]:
    """Run one profiling repetition against the live service pipeline.

    Requires:
    - VERBATIM_PERF_LIVE=1 env var (enforced by caller)
    - Service running at VERBATIM_PERF_SERVICE_URL (default http://127.0.0.1:8000)
    - FFmpeg + Whisper model provisioned on the endpoint
    - VERBATIM_PERF_LIVE guard already checked by _collect_scenarios
    """
    import tempfile
    import urllib.error
    import urllib.parse
    import urllib.request

    base_url = os.getenv("VERBATIM_PERF_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")

    # 1. Get session token
    with urllib.request.urlopen(f"{base_url}/api/session", timeout=10) as resp:
        session = json.loads(resp.read().decode())
    token = session["request_token"]

    # 2. Generate synthetic WAV of target size
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / f"synth_{size_mb:.0f}mb.wav"
        _synth_wav(size_mb, wav_path)

        # 3. POST to /api/jobs
        boundary = "VerbatimProf" + str(int(time.monotonic() * 1000))
        body_parts = []
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="consent_confirmed"\r\n\r\ntrue\r\n'
        )
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nauto\r\n'
        )
        file_bytes = wav_path.read_bytes()
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{wav_path.name}"\r\nContent-Type: audio/wav\r\n\r\n'
        )
        body_bin = (
            "".join(body_parts).encode()
            + file_bytes
            + f"\r\n--{boundary}--\r\n".encode()
        )

        upload_req = urllib.request.Request(
            f"{base_url}/api/jobs",
            data=body_bin,
            method="POST",
        )
        upload_req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        upload_req.add_header("X-Request-Token", token)

        t_submit = time.monotonic()
        try:
            with urllib.request.urlopen(upload_req, timeout=30) as resp:
                job_data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise RuntimeError(f"Upload failed HTTP {exc.code}: {body}") from exc

    job_id = job_data.get("job_id") or job_data.get("id")
    if not job_id:
        raise RuntimeError(f"No job_id in upload response: {job_data}")

    # 4. Poll until done, tracking wall time
    # Optional: sample CPU/RSS if psutil is available
    cpu_samples: list[float] = []
    rss_samples: list[float] = []
    try:
        import psutil  # type: ignore[import]
        proc = psutil.Process()
        _has_psutil = True
    except ImportError:
        _has_psutil = False

    def _sample_resources() -> None:
        if not _has_psutil:
            return
        try:
            cpu_samples.append(psutil.cpu_percent(interval=None))
            rss_samples.append(proc.memory_info().rss / 1024 / 1024)
        except Exception:
            pass

    poll_start = time.monotonic()
    deadline = poll_start + 1800.0
    while time.monotonic() < deadline:
        _sample_resources()
        req = urllib.request.Request(f"{base_url}/api/jobs/{job_id}")
        req.add_header("X-Request-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Poll failed: {exc}") from exc
        status = data.get("status", "")
        if status in {"complete", "failed", "error"}:
            break
        time.sleep(2.0)
    else:
        return {"elapsed_seconds": 1800.0, "peak_cpu_pct": 0.0, "peak_rss_mb": 0.0,
                "temp_storage_mb": size_mb, "failed": True}

    elapsed = time.monotonic() - t_submit
    return {
        "elapsed_seconds": round(elapsed, 2),
        "peak_cpu_pct": round(max(cpu_samples, default=0.0), 1),
        "peak_rss_mb": round(max(rss_samples, default=0.0), 1),
        "temp_storage_mb": round(size_mb * 1.1, 2),
        "failed": status != "complete",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_report(
    protocol: dict[str, Any],
    scenarios: list[dict[str, Any]],
    mock: bool,
) -> dict[str, Any]:
    run_date = datetime.date.today().isoformat()
    return {
        "schema_version": "1.0",
        "run_id": f"docker-profiling-{run_date}",
        "run_date": run_date,
        "gate": "QG-06",
        "environment": "docker_dev_machine" if mock else "live",
        "not_qualified_endpoint": True,
        "mock_mode": mock,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "note": (
            "ASSUMPTION: Dev-machine Docker simulation. Results are NOT qualified-endpoint "
            "evidence. Managed corporate endpoint profiling required for QG-06 exit. "
            "P50/P95 values are from deterministic mock model, not real Whisper inference."
            if mock else
            "Live run on this machine. Still not qualified-endpoint evidence unless "
            "this machine is on the approved corporate endpoint matrix."
        ),
        "protocol_id": protocol.get("protocol_id", ""),
        "scenarios": scenarios,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verbatim QG-06 synthetic profiling")
    parser.add_argument("--fixtures-dir", default="tests/fixtures")
    parser.add_argument(
        "--output-dir",
        default="evidence/capacity",
        help="Directory where profiling JSON is written",
    )
    parser.add_argument(
        "--protocol",
        default="evidence/capacity/profiling-protocol.json",
        help="Path to profiling-protocol.json",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Use mock transcriber (safe for CI — default)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Use real pipeline (requires VERBATIM_PERF_LIVE=1 and Whisper model)",
    )
    parser.add_argument(
        "--service-url",
        default="http://127.0.0.1:8000",
        help="Service base URL for live mode (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args(argv)

    if args.live and not os.getenv("VERBATIM_PERF_SERVICE_URL"):
        os.environ["VERBATIM_PERF_SERVICE_URL"] = args.service_url

    if args.live:
        args.mock = False

    protocol_path = Path(args.protocol)
    if not protocol_path.exists():
        print(f"ERROR: protocol file not found: {protocol_path}", file=sys.stderr)
        return 2

    with protocol_path.open(encoding="utf-8") as f:
        protocol = json.load(f)

    print(f"Running profiling: mock={args.mock}, protocol={protocol_path}")
    t_start = time.monotonic()
    scenarios = _collect_scenarios(protocol, mock=args.mock)
    elapsed = time.monotonic() - t_start
    print(f"Completed {len(scenarios)} scenarios in {elapsed:.1f}s")

    report = _build_report(protocol, scenarios, mock=args.mock)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"docker-profiling-{report['run_date']}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Results written to {out_path}")

    # Exit non-zero if any scenario failed (not PENDING_HUMAN)
    failures = [s for s in scenarios if s.get("status") == "ALL_FAILED"]
    if failures:
        print(f"ERROR: {len(failures)} scenario(s) ALL_FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
