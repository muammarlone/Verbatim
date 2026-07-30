"""QG-06: Endpoint performance measurement script.

Usage:
    python scripts/run_endpoint_perf.py [--output PATH] [--media PATH]

Measures wall time, approximate peak memory, and temp-storage delta for a
single-recording transcription job using the live API via TestClient.
Output is a JSON evidence record for the endpoint platform lead to review.

IMPORTANT: This script measures on the host it runs on. For QG-06 sign-off,
it must be executed on the qualified managed Windows endpoint by the named
endpoint platform lead. Developer-machine results do not satisfy the gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from secure_transcribe.analysis import analyze_transcript
from secure_transcribe.app import create_app
from secure_transcribe.config import Settings
from secure_transcribe.models import JobStatus, TranscriptDocument, TranscriptSegment, utc_now


MP4_MAGIC = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom"

SYNTHETIC_FIXTURE = ROOT / "tests" / "fixtures" / "sample.mp4"

CLAIM_BOUNDARY = (
    "Measurement from test-client API call using synthetic fixture only. "
    "Real-world performance on qualified hardware requires execution by the "
    "named endpoint platform lead (QG-06). No throughput or latency guarantee "
    "is implied by these numbers."
)


class _ReadyMedia:
    @staticmethod
    def is_ffmpeg_ready() -> bool:
        return True

    @staticmethod
    def is_ffprobe_ready() -> bool:
        return True

    def probe(self, source):
        raise AssertionError("unexpected")

    def extract_audio(self, source, destination):
        raise AssertionError("unexpected")


class _ReadyTranscriber:
    model_id = "fixture-model:v1"

    @staticmethod
    def is_ready() -> bool:
        return True

    def transcribe(self, audio_path, language):
        raise AssertionError("unexpected")


class _InstantProcessor:
    def __init__(self, store, *_):
        self.store = store

    def submit(self, job_id: str) -> None:
        segments = [
            TranscriptSegment(id=0, start=0, end=5, text="Synthetic fixture transcript."),
        ]
        transcript = TranscriptDocument(
            job_id=job_id,
            language="en",
            duration_seconds=5,
            model_id="fixture-model:v1",
            created_at=utc_now(),
            segments=segments,
            text="Synthetic fixture transcript.",
        )
        self.store.write_transcript(transcript)
        self.store.write_analysis(analyze_transcript(transcript))
        self.store.update_job(
            job_id,
            status=JobStatus.COMPLETE,
            progress=100,
            duration_seconds=5,
            detected_language="en",
            segment_count=1,
        )

    def shutdown(self) -> None:
        return None


def measure(tmp_path: Path, media_bytes: bytes) -> dict:
    model = tmp_path / "base.pt"
    model.write_bytes(b"fixture")
    settings = Settings(data_dir=tmp_path / "data", model_path=model, max_upload_bytes=10 * 1024 * 1024)
    app = create_app(
        settings,
        media=_ReadyMedia(),
        transcriber=_ReadyTranscriber(),
        processor_factory=lambda store, *args: _InstantProcessor(store),
    )

    tracemalloc.start()
    data_dir_before = _dir_size(tmp_path / "data")
    wall_start = time.perf_counter()

    with TestClient(app) as client:
        token = client.get("/api/session").json()["request_token"]
        response = client.post(
            "/api/jobs",
            headers={"X-Studio-Token": token},
            files={"file": ("synthetic.mp4", media_bytes, "video/mp4")},
            data={"language": "auto", "consent_confirmed": "true"},
        )
        assert response.status_code == 202, f"Unexpected status: {response.status_code}"
        job = response.json()["job"]
        assert job["status"] == "complete"

    wall_seconds = time.perf_counter() - wall_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    data_dir_after = _dir_size(tmp_path / "data")

    return {
        "_schema": "endpoint-perf-evidence/1.0",
        "_status": "synthetic-testclient-run",
        "_gate": "QG-06",
        "date": time.strftime("%Y-%m-%d"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "model_id": "fixture-model:v1 (synthetic only)",
        "media_bytes": len(media_bytes),
        "wall_seconds": round(wall_seconds, 3),
        "peak_memory_mb": round(peak_bytes / 1024 / 1024, 2),
        "temp_storage_delta_kb": round((data_dir_after - data_dir_before) / 1024, 1),
        "outcome": "complete",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verbatim endpoint performance measurement (synthetic fixture)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON evidence to this path (e.g. evidence/endpoint/perf-short.json)",
    )
    args = parser.parse_args()

    import tempfile

    print("Verbatim endpoint performance measurement — SYNTHETIC only")
    print(f"CLAIM BOUNDARY: {CLAIM_BOUNDARY}")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        result = measure(Path(tmp), MP4_MAGIC)

    print(f"Wall time      : {result['wall_seconds']} s")
    print(f"Peak memory    : {result['peak_memory_mb']} MB")
    print(f"Temp storage Δ : {result['temp_storage_delta_kb']} KB")
    print()

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Evidence written: {out}")
        print()
        print(
            "NOTE: Replace this file with a measurement from the qualified managed endpoint "
            "signed by the named endpoint platform lead before QG-06 can be marked passed."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
