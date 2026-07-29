from datetime import timedelta

from secure_transcribe.analysis import analyze_transcript
from secure_transcribe.models import TranscriptDocument, TranscriptSegment, utc_now


def sample_transcript() -> TranscriptDocument:
    segments = [
        TranscriptSegment(
            id=0, start=0, end=8, text="Today we will review the migration timeline."
        ),
        TranscriptSegment(
            id=1, start=8, end=17, text="Jordan will follow up with security by Friday."
        ),
        TranscriptSegment(id=2, start=17, end=25, text="What evidence do we need for approval?"),
        TranscriptSegment(
            id=3,
            start=25,
            end=60,
            text="The migration plan covers testing, migration, and rollback.",
        ),
    ]
    return TranscriptDocument(
        job_id="00000000-0000-0000-0000-000000000001",
        language="en",
        duration_seconds=60,
        model_id="fixture:v1",
        created_at=utc_now() - timedelta(seconds=1),
        segments=segments,
        text=" ".join(segment.text for segment in segments),
    )


def test_analysis_is_deterministic_and_review_first() -> None:
    first = analyze_transcript(sample_transcript())
    second = analyze_transcript(sample_transcript())
    assert first.model_dump(exclude={"generated_at"}) == second.model_dump(exclude={"generated_at"})
    assert first.word_count == 25
    assert first.words_per_minute == 25
    assert {item.segment_id for item in first.action_candidates} == {0, 1}
    assert first.questions[0].segment_id == 2
    assert any("require review" in item for item in first.limitations)
    assert first.method == "deterministic-extractive-v1"
