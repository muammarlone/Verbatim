from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def transform_time(value: float, start: float, end: float, speed: float) -> float:
    if value <= start:
        return value
    if value <= end:
        return start + (value - start) / speed
    return start + (end - start) / speed + (value - end)


def main() -> None:
    parser = argparse.ArgumentParser(description="Condense the measured batch-processing wait.")
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--speed", type=float, default=16.0)
    args = parser.parse_args()
    run_directory = args.run_directory.resolve()
    report = json.loads(
        (run_directory / "recording-report.json").read_text(encoding="utf-8")
    )
    source_path = run_directory / "verbatim-batch-demo-visual.webm"
    milestones = report["milestones"]
    accelerate_start = float(milestones["batch_started"]) + 4.0
    accelerate_end = float(milestones["batch_complete"]) - 5.0
    trim_end = float(milestones["cleanup_complete"]) + 7.0
    if accelerate_end <= accelerate_start:
        raise SystemExit("Batch-processing interval is too short to condense.")

    output_path = run_directory / "verbatim-batch-demo-condensed.mp4"
    font = "C\\:/Windows/Fonts/segoeuib.ttf"
    label = (
        "drawbox=x=w-560:y=h-76:w=532:h=50:color=0x17201D@0.92:t=fill,"
        f"drawtext=fontfile='{font}':text='2 LOCAL TRANSCRIPTIONS - PLAYBACK {args.speed:g}x':"
        "fontcolor=white:fontsize=19:x=w-tw-44:y=h-th-40"
    )
    filter_graph = (
        f"[0:v]split=3[v0s][v1s][v2s];"
        f"[v0s]trim=start=0:end={accelerate_start:.3f},setpts=PTS-STARTPTS[v0];"
        f"[v1s]trim=start={accelerate_start:.3f}:end={accelerate_end:.3f},"
        f"setpts=(PTS-STARTPTS)/{args.speed:.6f},{label}[v1];"
        f"[v2s]trim=start={accelerate_end:.3f}:end={trim_end:.3f},setpts=PTS-STARTPTS[v2];"
        "[v0][v1][v2]concat=n=3:v=1:a=0[vout]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_path),
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=True,
    )

    condensed = dict(report)
    condensed["source_visual_video"] = report["visual_video"]
    condensed["visual_video"] = str(output_path)
    condensed["milestones"] = {
        key: round(transform_time(float(value), accelerate_start, accelerate_end, args.speed), 3)
        for key, value in milestones.items()
    }
    condensed["processing_edit"] = {
        "source_wall_seconds": report["processing_wall_seconds"],
        "accelerated_interval_start": round(accelerate_start, 3),
        "accelerated_interval_end": round(accelerate_end, 3),
        "playback_speed": args.speed,
        "visible_disclosure": True,
        "trim_end_source_seconds": round(trim_end, 3),
    }
    (run_directory / "condensed-report.json").write_text(
        json.dumps(condensed, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(condensed, indent=2))


if __name__ == "__main__":
    main()
