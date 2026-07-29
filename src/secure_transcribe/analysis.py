from __future__ import annotations

import math
import re
from collections import Counter

from .models import AnalysisItem, AnalysisReport, TermCount, TranscriptDocument, utc_now

_WORDS = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
_ACTION_PATTERN = re.compile(
    r"\b(action|assign|follow up|need to|must|should|will|deadline|due|owner)\b", re.I
)
_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "been",
    "before",
    "being",
    "but",
    "can",
    "could",
    "did",
    "does",
    "for",
    "from",
    "have",
    "into",
    "just",
    "like",
    "more",
    "not",
    "now",
    "our",
    "that",
    "the",
    "their",
    "then",
    "there",
    "they",
    "this",
    "through",
    "was",
    "what",
    "when",
    "where",
    "which",
    "will",
    "with",
    "would",
    "you",
    "your",
}


def analyze_transcript(document: TranscriptDocument) -> AnalysisReport:
    words = [match.group(0).lower() for match in _WORDS.finditer(document.text)]
    terms = Counter(word for word in words if word not in _STOPWORDS)
    top_terms = [TermCount(term=term, count=count) for term, count in terms.most_common(10)]

    scored: list[tuple[float, int]] = []
    for segment in document.segments:
        segment_words = [match.group(0).lower() for match in _WORDS.finditer(segment.text)]
        if not segment_words:
            continue
        score = sum(terms.get(word, 0) for word in set(segment_words)) / math.sqrt(
            len(segment_words)
        )
        scored.append((score, segment.id))

    key_ids = {
        segment_id for _, segment_id in sorted(scored, key=lambda item: item[0], reverse=True)[:5]
    }
    key_moments = [
        AnalysisItem(
            segment_id=segment.id,
            timestamp_seconds=segment.start,
            text=segment.text,
        )
        for segment in document.segments
        if segment.id in key_ids
    ]
    action_candidates = [
        AnalysisItem(segment_id=item.id, timestamp_seconds=item.start, text=item.text)
        for item in document.segments
        if _ACTION_PATTERN.search(item.text)
    ][:12]
    questions = [
        AnalysisItem(segment_id=item.id, timestamp_seconds=item.start, text=item.text)
        for item in document.segments
        if "?" in item.text
    ][:12]
    minutes = document.duration_seconds / 60 if document.duration_seconds else 0
    return AnalysisReport(
        job_id=document.job_id,
        generated_at=utc_now(),
        word_count=len(words),
        speaking_minutes=round(minutes, 2),
        words_per_minute=round(len(words) / minutes, 1) if minutes else 0,
        top_terms=top_terms,
        key_moments=key_moments,
        action_candidates=action_candidates,
        questions=questions,
        limitations=[
            "Key moments are selected by term frequency, not human judgment.",
            "Action candidates are keyword matches and require review.",
            "Speaker identification and sentiment scoring are not included in this release.",
        ],
    )
