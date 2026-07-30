from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_link_errors(path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for target in LINK.findall(text):
        clean = unquote(target.split("#", 1)[0].strip())
        if not clean or clean.startswith(("http://", "https://", "mailto:")):
            continue
        candidate = (path.parent / clean).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.exists():
            errors.append(f"{path.relative_to(root)}: broken local link {target}")
    return errors


def probe_video(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,r_frame_rate,channels,sample_rate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def validate_product_evidence(root: Path = ROOT, *, verify_streams: bool = True) -> list[str]:
    errors: list[str] = []
    required = [
        root / "docs" / "USER_MANUAL.md",
        root / "docs" / "FEATURES_AND_LIMITATIONS.md",
        root / "evidence" / "explainer" / "README.md",
        root / "evidence" / "explainer" / "explainer-script.md",
        root / "evidence" / "explainer" / "explainer-evidence.json",
        root / "evidence" / "explainer" / "verbatim-grounded-product-explainer.mp4",
        root / "evidence" / "explainer" / "explainer-poster.png",
        root / "evidence" / "explainer" / "explainer-contact-sheet.png",
        root / "evidence" / "verification.json",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        return [f"missing required product evidence: {', '.join(missing)}"]

    verification = json.loads((root / "evidence" / "verification.json").read_text(encoding="utf-8"))
    report_path = root / "evidence" / "explainer" / "explainer-evidence.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    video = root / report["video"]
    if sha256(video) != report.get("sha256"):
        errors.append("explainer video SHA-256 does not match explainer-evidence.json")

    for source in report.get("source_videos", []):
        source_path = root / source["path"]
        if not source_path.is_file() or sha256(source_path) != source.get("sha256"):
            errors.append(f"source video hash mismatch: {source['path']}")

    manual = (root / "docs" / "USER_MANUAL.md").read_text(encoding="utf-8")
    features = (root / "docs" / "FEATURES_AND_LIMITATIONS.md").read_text(encoding="utf-8")
    script = (root / "evidence" / "explainer" / "explainer-script.md").read_text(
        encoding="utf-8"
    )
    evidence_readme = (root / "evidence" / "explainer" / "README.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((manual, features, script, evidence_readme))
    expected_metrics = (
        str(verification["automated_tests"]["passed"]),
        str(verification["automated_tests"]["coverage_percent"]),
        str(verification["architecture_evaluation"]["passed"]),
    )
    for metric in expected_metrics:
        if metric not in combined:
            errors.append(f"current verification metric is absent from product documentation: {metric}")

    required_boundaries = [
        "not available",
        "disabled by default",
        "not a general accuracy claim",
        "not a defensible product claim",
        "does not establish general transcription accuracy",
    ]
    lowered = " ".join(combined.lower().split())
    for phrase in required_boundaries:
        if phrase not in lowered:
            errors.append(f"required claim boundary is missing: {phrase}")
    if "password-protected zip/7z extraction | not available" not in features.lower():
        errors.append("protected-archive capability status is not fail-closed in the reference")
    zoom_rows = [line for line in features.lower().splitlines() if "zoom" in line and "not available" in line]
    if not zoom_rows:
        errors.append("Zoom capability status is not fail-closed in the reference")

    if report.get("scenes") != 10:
        errors.append("explainer scene count must remain 10")
    report_boundary = str(report.get("claim_boundary", "")).lower()
    if not all(term in report_boundary for term in ("synthetic", "no general accuracy")):
        errors.append("explainer report claim boundary is missing required limits")
    if report.get("sha256") not in evidence_readme:
        errors.append("explainer README does not contain the machine evidence hash")

    for document in required[:4]:
        errors.extend(local_link_errors(document, root))
    errors.extend(local_link_errors(root / "README.md", root))

    if verify_streams:
        try:
            probe = probe_video(video)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            errors.append(f"ffprobe could not validate the explainer: {type(exc).__name__}")
        else:
            streams = probe.get("streams", [])
            video_stream = next(
                (stream for stream in streams if stream.get("codec_type") == "video"), None
            )
            audio_stream = next(
                (stream for stream in streams if stream.get("codec_type") == "audio"), None
            )
            if not video_stream or (
                video_stream.get("codec_name"),
                video_stream.get("width"),
                video_stream.get("height"),
                video_stream.get("r_frame_rate"),
            ) != ("h264", 1440, 900, "25/1"):
                errors.append("explainer video stream must be 1440x900 H.264 at 25 fps")
            if not audio_stream or (
                audio_stream.get("codec_name"),
                audio_stream.get("channels"),
                audio_stream.get("sample_rate"),
            ) != ("aac", 1, "48000"):
                errors.append("explainer audio stream must be mono AAC at 48 kHz")
            actual_duration = float(probe["format"]["duration"])
            if abs(actual_duration - float(report.get("duration_seconds", 0))) > 0.05:
                errors.append("explainer duration does not match machine evidence")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate grounded product documentation and video evidence."
    )
    parser.add_argument("--no-streams", action="store_true", help="Skip FFprobe stream checks.")
    args = parser.parse_args()
    errors = validate_product_evidence(verify_streams=not args.no_streams)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)
    print("PRODUCT EVIDENCE VALIDATED: docs, claims, links, hashes, metrics, and media passed")


if __name__ == "__main__":
    main()
