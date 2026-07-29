from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import StudioError
from .models import AnalysisReport, TranscriptDocument

SUPPORTED_EXPORT_FORMATS = ("txt", "srt", "vtt", "md", "json")


def safe_export_base(display_name: str) -> str:
    base = Path(display_name).stem[:100] or "transcript"
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)


def _timestamp(seconds: float, separator: str = ",") -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{separator}{milliseconds:03}"


def render_export(
    transcript: TranscriptDocument, analysis: AnalysisReport, export_format: str
) -> tuple[str, str, str]:
    export_format = export_format.lower()
    if export_format == "txt":
        return transcript.text + "\n", "text/plain; charset=utf-8", "txt"
    if export_format == "json":
        payload = {
            "transcript": transcript.model_dump(mode="json"),
            "analysis": analysis.model_dump(mode="json"),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "application/json", "json"
    if export_format == "srt":
        blocks = [
            f"{index}\n{_timestamp(segment.start)} --> {_timestamp(segment.end)}\n{segment.text}"
            for index, segment in enumerate(transcript.segments, start=1)
        ]
        return "\n\n".join(blocks) + "\n", "application/x-subrip; charset=utf-8", "srt"
    if export_format == "vtt":
        blocks = [
            f"{_timestamp(segment.start, '.')} --> {_timestamp(segment.end, '.')}\n{segment.text}"
            for segment in transcript.segments
        ]
        return "WEBVTT\n\n" + "\n\n".join(blocks) + "\n", "text/vtt; charset=utf-8", "vtt"
    if export_format == "md":
        moments = (
            "\n".join(
                f"- [{_timestamp(item.timestamp_seconds, '.')}](#) {item.text}"
                for item in analysis.key_moments
            )
            or "- None detected"
        )
        body = (
            "# Transcript\n\n"
            f"- Language: {transcript.language}\n"
            f"- Model: {transcript.model_id}\n"
            f"- Duration: {transcript.duration_seconds:.1f} seconds\n\n"
            "## Key moments\n\n"
            f"{moments}\n\n"
            "## Full text\n\n"
            f"{transcript.text}\n"
        )
        return body, "text/markdown; charset=utf-8", "md"
    raise StudioError("UNSUPPORTED_EXPORT", "Choose TXT, SRT, VTT, Markdown, or JSON.")
