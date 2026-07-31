"""Production-like synthetic evaluation fixtures for QG-01.

Each EvalCase pairs a reference transcript (what a human reviewer would write)
with a hypothesis (what Whisper-class models actually produce under the stated
conditions). Hypothesis strings simulate realistic model error patterns:

  - Number formatting divergence: "200 mg" vs "two hundred milligrams"
  - Filler word handling: Whisper often drops or retains "um", "uh"
  - Domain term substitution: "hypertension" → "hyper tension" (word split)
  - Homophone confusion: "board" → "bored", "principal" → "principle"
  - Punctuation: Whisper inserts/omits sentence-boundary punctuation variably
  - Proper noun mishearing: "Pfizer" → "Pfizer" (usually right), "ChatGPT" → "chat GPT"
  - Multi-speaker: speaker turns sometimes merged or truncated
  - Noisy audio: extra words inserted, words dropped, substitutions increase
  - Non-English: character accents, ligatures, number formatting

WER thresholds reflect the level that a human reviewer can correct in a
review pass without material meaning loss. They are NOT accuracy claims.
All cases are synthetic; a sealed production dataset with domain eval lead
approval is required before any result supports a QG-01 pilot decision.
"""
from __future__ import annotations

from tests.eval.eval_harness import SYNTHETIC_MARKER, EvalCase


# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / GENERAL / CLEAN / SINGLE SPEAKER — baseline coverage
# ──────────────────────────────────────────────────────────────────────────────

EN_GENERAL_CLEAN = [
    EvalCase(
        id="syn-en-gen-001",
        reference="We will document the local review.",
        hypothesis="We will document the local review.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-gen-002",
        reference="What should happen next?",
        hypothesis="What should happen next?",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-gen-003",
        reference="The meeting is scheduled for Tuesday at two o'clock.",
        hypothesis="The meeting is scheduled for Tuesday at two o'clock.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-gen-004",
        reference="Please send the updated draft to everyone on the distribution list.",
        hypothesis="Please send the updated draft to everyone on the distribution list.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-gen-005",
        # Whisper: trailing punctuation occasionally dropped in mid-sentence
        reference="The action items are due by end of week, not end of month.",
        hypothesis="The action items are due by end of week not end of month.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.05,
    ),
    EvalCase(
        id="syn-en-gen-006",
        # Whisper: smart quotes sometimes transcribed as straight quotes or dropped
        reference="She said \"we need to move faster\" and everyone agreed.",
        hypothesis="She said we need to move faster and everyone agreed.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.05,
    ),
    EvalCase(
        id="syn-en-gen-007",
        # Number formatting: spoken "twenty-five percent" sometimes written as "25%"
        reference="Revenue grew by twenty-five percent year over year.",
        hypothesis="Revenue grew by 25% year over year.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
    EvalCase(
        id="syn-en-gen-008",
        # Proper noun: acronym expansion — "AI" spoken as "A. I." sometimes merged
        reference="The A.I. team will present their findings on Friday.",
        hypothesis="The AI team will present their findings on Friday.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / GENERAL / NOISY — background noise simulation
# ──────────────────────────────────────────────────────────────────────────────

EN_GENERAL_NOISY = [
    EvalCase(
        id="syn-en-noisy-001",
        reference="Please review the attached documents before the meeting.",
        hypothesis="Please review the attached documents before the meeting",
        language="en", noise_level="noisy", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-en-noisy-002",
        # Noise: word dropped at edge of utterance
        reference="We need to finalise the contract by end of quarter.",
        hypothesis="We need to finalise the contract by end of the quarter.",
        language="en", noise_level="noisy", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-en-noisy-003",
        # Noise: substitution of a short word under background noise
        reference="The board approved the revised budget on Thursday.",
        hypothesis="The board approved the revised budget on Tuesday.",
        language="en", noise_level="noisy", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.12,
    ),
    EvalCase(
        id="syn-en-noisy-004",
        # Noise: word insertion (Whisper hallucinates brief noise as a word)
        reference="All open items have been resolved.",
        hypothesis="All open items have now been resolved.",
        language="en", noise_level="noisy", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
    EvalCase(
        id="syn-en-noisy-005",
        # Severe noise: multiple errors across a short sentence
        reference="Sign the form and return it by Friday.",
        hypothesis="Sign the form and return by Friday.",
        language="en", noise_level="noisy", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / MEDICAL — domain vocabulary
# ──────────────────────────────────────────────────────────────────────────────

EN_MEDICAL = [
    EvalCase(
        id="syn-en-med-001",
        reference="The patient presented with hypertension and tachycardia.",
        hypothesis="The patient presented with hypertension and tachycardia.",
        language="en", noise_level="clean", speaker_count=1, domain="medical",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-med-002",
        # Whisper: "milligrams" sometimes written as digits
        reference="Dosage should not exceed two hundred milligrams per day.",
        hypothesis="Dosage should not exceed 200 milligrams per day.",
        language="en", noise_level="clean", speaker_count=1, domain="medical",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
    EvalCase(
        id="syn-en-med-003",
        # Domain term split: "myocardial" → "my ocardial" (uncommon term)
        reference="Myocardial infarction was ruled out by troponin assay.",
        hypothesis="My ocardial infarction was ruled out by troponin assay.",
        language="en", noise_level="clean", speaker_count=1, domain="medical",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-en-med-004",
        # Multi-syllable: "contraindication" sometimes split
        reference="The primary contraindication is severe renal impairment.",
        hypothesis="The primary contra indication is severe renal impairment.",
        language="en", noise_level="clean", speaker_count=1, domain="medical",
        source=SYNTHETIC_MARKER, wer_threshold=0.08,
    ),
    EvalCase(
        id="syn-en-med-005",
        # Noisy medical: higher error rate in clinical background noise
        reference="Blood pressure was one forty over ninety on admission.",
        hypothesis="Blood pressure was 140 over 90 on admission.",
        language="en", noise_level="noisy", speaker_count=1, domain="medical",
        source=SYNTHETIC_MARKER, wer_threshold=0.20,
    ),
    EvalCase(
        id="syn-en-med-006",
        # Latin abbreviation spoken: "PRN" sometimes kept or expanded
        reference="Administer acetaminophen PRN for pain management.",
        hypothesis="Administer acetaminophen P R N for pain management.",
        language="en", noise_level="clean", speaker_count=1, domain="medical",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / LEGAL — domain vocabulary
# ──────────────────────────────────────────────────────────────────────────────

EN_LEGAL = [
    EvalCase(
        id="syn-en-legal-001",
        reference="The deposition was conducted pursuant to federal rule thirty.",
        hypothesis="The deposition was conducted pursuant to federal rule thirty.",
        language="en", noise_level="clean", speaker_count=1, domain="legal",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-legal-002",
        # "subpoena" sometimes transcribed with space
        reference="The subpoena was served on the defendant's counsel.",
        hypothesis="The sub poena was served on the defendant's counsel.",
        language="en", noise_level="clean", speaker_count=1, domain="legal",
        source=SYNTHETIC_MARKER, wer_threshold=0.08,
    ),
    EvalCase(
        id="syn-en-legal-003",
        # "voir dire" — French loanword, often mishears
        reference="Voir dire examination of the prospective jurors will begin at nine.",
        hypothesis="War deer examination of the prospective jurors will begin at nine.",
        language="en", noise_level="clean", speaker_count=1, domain="legal",
        source=SYNTHETIC_MARKER, wer_threshold=0.12,
    ),
    EvalCase(
        id="syn-en-legal-004",
        reference="Counsel stipulated that the exhibit would be admitted without objection.",
        hypothesis="Counsel stipulated that the exhibit would be admitted without objection.",
        language="en", noise_level="clean", speaker_count=1, domain="legal",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / FINANCE — domain vocabulary
# ──────────────────────────────────────────────────────────────────────────────

EN_FINANCE = [
    EvalCase(
        id="syn-en-fin-001",
        reference="The budget review meeting will proceed as scheduled.",
        hypothesis="The budget review meeting will proceed as scheduled",
        language="en", noise_level="clean", speaker_count=1, domain="finance",
        source=SYNTHETIC_MARKER, wer_threshold=0.05,
    ),
    EvalCase(
        id="syn-en-fin-002",
        # "EBITDA" acronym — sometimes expanded or split
        reference="Adjusted EBITDA came in at forty-two million for the quarter.",
        hypothesis="Adjusted EBITDA came in at 42 million for the quarter.",
        language="en", noise_level="clean", speaker_count=1, domain="finance",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-en-fin-003",
        # "basis points" — sometimes "base is points"
        reference="The central bank raised rates by fifty basis points.",
        hypothesis="The central bank raised rates by 50 basis points.",
        language="en", noise_level="clean", speaker_count=1, domain="finance",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-en-fin-004",
        # P&L: spoken as "P and L", sometimes "peanut L" or "P N L"
        reference="The P&L shows a net loss of three million dollars.",
        hypothesis="The P and L shows a net loss of 3 million dollars.",
        language="en", noise_level="clean", speaker_count=1, domain="finance",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
    EvalCase(
        id="syn-en-fin-005",
        reference="Year-over-year revenue growth was twelve percent.",
        hypothesis="Year-over-year revenue growth was 12 percent.",
        language="en", noise_level="clean", speaker_count=1, domain="finance",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / COMPLIANCE — regulatory and HR contexts
# ──────────────────────────────────────────────────────────────────────────────

EN_COMPLIANCE = [
    EvalCase(
        id="syn-en-comp-001",
        reference="All employees must complete mandatory training by December thirty-first.",
        hypothesis="All employees must complete mandatory training by December 31st.",
        language="en", noise_level="clean", speaker_count=1, domain="compliance",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
    EvalCase(
        id="syn-en-comp-002",
        reference="The incident was escalated to the privacy officer within forty-eight hours.",
        hypothesis="The incident was escalated to the privacy officer within 48 hours.",
        language="en", noise_level="clean", speaker_count=1, domain="compliance",
        source=SYNTHETIC_MARKER, wer_threshold=0.10,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# ENGLISH / MULTI-SPEAKER — two or more speakers
# ──────────────────────────────────────────────────────────────────────────────

EN_MULTI_SPEAKER = [
    EvalCase(
        id="syn-en-multi-001",
        reference="Team lead: All systems are go. Engineer: Confirmed, no blockers.",
        hypothesis="Team lead: All systems are go. Engineer: Confirmed, no blockers.",
        language="en", noise_level="clean", speaker_count=2, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-en-multi-002",
        # Multi-speaker: speaker attribution marker sometimes lost
        reference="Chair: The motion is tabled. Member: I second that.",
        hypothesis="The motion is tabled. I second that.",
        language="en", noise_level="clean", speaker_count=2, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.25,
    ),
    EvalCase(
        id="syn-en-multi-003",
        # Multi-speaker noisy: overlap causes word insertion
        reference="First speaker: We will reconvene at three. Second speaker: Understood.",
        hypothesis="We will reconvene at three. Understood.",
        language="en", noise_level="noisy", speaker_count=2, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.30,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# SPANISH — non-English coverage
# ──────────────────────────────────────────────────────────────────────────────

ES_GENERAL = [
    EvalCase(
        id="syn-es-gen-001",
        reference="La reunión comenzará a las nueve de la mañana.",
        hypothesis="La reunión comenzará a las nueve de la mañana.",
        language="es", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-es-gen-002",
        # Number formatting
        reference="El presupuesto asignado es de cien mil euros.",
        hypothesis="El presupuesto asignado es de 100.000 euros.",
        language="es", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
    EvalCase(
        id="syn-es-gen-003",
        reference="Por favor, revise el informe antes de la presentación.",
        hypothesis="Por favor, revise el informe antes de la presentación.",
        language="es", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# FRENCH — non-English coverage
# ──────────────────────────────────────────────────────────────────────────────

FR_GENERAL = [
    EvalCase(
        id="syn-fr-gen-001",
        reference="Le rapport sera prêt avant la fin de la semaine.",
        hypothesis="Le rapport sera prêt avant la fin de la semaine.",
        language="fr", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-fr-gen-002",
        # French ligature and accent handling
        reference="Nous devons améliorer notre efficacité opérationnelle.",
        hypothesis="Nous devons améliorer notre efficacité opérationnelle.",
        language="fr", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-fr-gen-003",
        # French: numbers sometimes digit-formatted
        reference="La réunion est prévue pour le quinze mars à quatorze heures.",
        hypothesis="La réunion est prévue pour le 15 mars à 14 heures.",
        language="fr", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.15,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# GERMAN — additional non-English coverage
# ──────────────────────────────────────────────────────────────────────────────

DE_GENERAL = [
    EvalCase(
        id="syn-de-gen-001",
        reference="Das Protokoll wird bis Freitag fertiggestellt.",
        hypothesis="Das Protokoll wird bis Freitag fertiggestellt.",
        language="de", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-de-gen-002",
        # Compound word: German compounds sometimes split incorrectly
        reference="Die Qualitätssicherung muss vor dem Release abgeschlossen sein.",
        hypothesis="Die Qualitäts sicherung muss vor dem Release abgeschlossen sein.",
        language="de", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.08,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# EDGE CASES — boundary behavior
# ──────────────────────────────────────────────────────────────────────────────

EDGE_CASES = [
    EvalCase(
        id="syn-edge-001-single-word",
        reference="Adjourned.",
        hypothesis="Adjourned.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.0,
    ),
    EvalCase(
        id="syn-edge-002-long-sentence",
        reference=(
            "The executive team has reviewed all outstanding action items from the "
            "previous quarter and unanimously agreed that the proposed timeline for "
            "the product launch should be extended by six weeks to allow for "
            "additional quality assurance testing."
        ),
        hypothesis=(
            "The executive team has reviewed all outstanding action items from the "
            "previous quarter and unanimously agreed that the proposed timeline for "
            "the product launch should be extended by 6 weeks to allow for "
            "additional quality assurance testing."
        ),
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.05,
    ),
    EvalCase(
        id="syn-edge-003-numbers-spoken",
        # All-numbers sentence: formats diverge most strongly here
        reference="The total is one thousand four hundred and twenty-two dollars and fifty cents.",
        hypothesis="The total is $1,422.50.",
        language="en", noise_level="clean", speaker_count=1, domain="finance",
        source=SYNTHETIC_MARKER, wer_threshold=0.70,  # high threshold: acceptable after review
    ),
    EvalCase(
        id="syn-edge-004-homophone",
        # Classic homophone error: meaning changes
        reference="The principal concern is data security.",
        hypothesis="The principle concern is data security.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.05,
    ),
    EvalCase(
        id="syn-edge-005-filler-words",
        # Whisper: filler words (um, uh) sometimes retained, sometimes dropped
        reference="Um, so, I think we need to, uh, revisit the roadmap.",
        hypothesis="So I think we need to revisit the roadmap.",
        language="en", noise_level="clean", speaker_count=1, domain="general",
        source=SYNTHETIC_MARKER, wer_threshold=0.25,
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# Combined fixture set — all synthetic cases
# ──────────────────────────────────────────────────────────────────────────────

ALL_SYNTHETIC_CASES: list[EvalCase] = (
    EN_GENERAL_CLEAN
    + EN_GENERAL_NOISY
    + EN_MEDICAL
    + EN_LEGAL
    + EN_FINANCE
    + EN_COMPLIANCE
    + EN_MULTI_SPEAKER
    + ES_GENERAL
    + FR_GENERAL
    + DE_GENERAL
    + EDGE_CASES
)

# Subsets for targeted gate work
SUBGROUP_LANGUAGE = {lang: [c for c in ALL_SYNTHETIC_CASES if c.language == lang]
                     for lang in ("en", "es", "fr", "de")}
SUBGROUP_NOISE = {level: [c for c in ALL_SYNTHETIC_CASES if c.noise_level == level]
                  for level in ("clean", "noisy")}
SUBGROUP_DOMAIN = {domain: [c for c in ALL_SYNTHETIC_CASES if c.domain == domain]
                   for domain in ("general", "medical", "legal", "finance", "compliance")}
SUBGROUP_SPEAKERS = {
    "single": [c for c in ALL_SYNTHETIC_CASES if c.speaker_count == 1],
    "multi": [c for c in ALL_SYNTHETIC_CASES if c.speaker_count > 1],
}
