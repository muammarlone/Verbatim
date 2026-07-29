import json

import pytest

from secure_transcribe.analysis import analyze_transcript
from secure_transcribe.errors import StudioError
from secure_transcribe.exports import render_export

from test_analysis import sample_transcript


@pytest.mark.parametrize(
    "format_name,expected",
    [("txt", "Today"), ("srt", "00:00:00,000"), ("vtt", "WEBVTT"), ("md", "# Transcript")],
)
def test_text_exports(format_name: str, expected: str) -> None:
    transcript = sample_transcript()
    body, media_type, extension = render_export(
        transcript, analyze_transcript(transcript), format_name
    )
    assert expected in body
    assert extension == format_name
    assert media_type


def test_json_export_preserves_provenance() -> None:
    transcript = sample_transcript()
    body, _, _ = render_export(transcript, analyze_transcript(transcript), "json")
    payload = json.loads(body)
    assert payload["transcript"]["model_id"] == "fixture:v1"
    assert payload["analysis"]["method"] == "deterministic-extractive-v1"


def test_unsupported_export_fails_closed() -> None:
    transcript = sample_transcript()
    with pytest.raises(StudioError) as exc:
        render_export(transcript, analyze_transcript(transcript), "docx")
    assert exc.value.code == "UNSUPPORTED_EXPORT"
