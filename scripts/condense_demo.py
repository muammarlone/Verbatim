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
    parser = argparse.ArgumentParser(description="Condense the measured processing wait in a demo.")
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--speed", type=float, default=12.0)
    args = parser.parse_args()
    run_directory = args.run_directory.resolve()
    report_path = run_directory / "recording-report.json"
    source_path = run_directory / "verbatim-demo-visual.webm"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    milestones = report["milestones"]
    accelerate_start = float(milestones["processing_started"]) + 3.5
    accelerate_end = float(milestones["job_complete"]) - 4.0
    trim_end = float(milestones["deleted"]) + 8.0
    if accelerate_end <= accelerate_start:
        raise SystemExit("Processing interval is too short to condense.")

    output_path = run_directory / "verbatim-demo-condensed.mp4"
    font = "C\\:/Windows/Fonts/segoeuib.ttf"
    label = (
        "drawbox=x=w-520:y=h-76:w=492:h=50:color=0x17201D@0.92:t=fill,"
        f"drawtext=fontfile='{font}':text='LOCAL TRANSCRIPTION - PLAYBACK {args.speed:g}x':"
        "fontcolor=white:fontsize=19:x=w-tw-44:y=h-th-40"
    )
    filter_graph = (
        f"[0:v]split=3[v0s][v1s][v2s];"
        f"[v0s]trim=start=0:end={accelerate_start:.3f},setpts=PTS-STARTPTS[v0];"
        f"[v1s]trim=start={accelerate_start:.3f}:end={accelerate_end:.3f},"
        f"setpts=(PTS-STARTPTS)/{args.speed:.6f},{label}[v1];"
        f"[v2s]trim=start={accelerate_end:.3f}:end={trim_end:.3f},"
        "setpts=PTS-STARTPTS[v2];"
        "[v0][v1][v2]concat=n=3:v=1:a=0[vout]"
    )
    command = [
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
    ]
    subprocess.run(command, check=True)

    condensed = dict(report)
    condensed["source_visual_video"] = report["visual_video"]
    condensed["visual_video"] = str(output_path)
    condensed["milestones"] = {
        key: round(transform_time(float(value), accelerate_start, accelerate_end, args.speed), 3)
        for key, value in milestones.items()
    }
    condensed["processing_edit"] = {
        "source_wall_seconds": round(
            float(milestones["job_complete"]) - float(milestones["processing_started"]), 3
        ),
        "accelerated_interval_start": round(accelerate_start, 3),
        "accelerated_interval_end": round(accelerate_end, 3),
        "playback_speed": args.speed,
        "visible_disclosure": True,
        "trim_end_source_seconds": round(trim_end, 3),
    }
    condensed_path = run_directory / "condensed-report.json"
    condensed_path.write_text(json.dumps(condensed, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(condensed, indent=2))


if __name__ == "__main__":
    main()
