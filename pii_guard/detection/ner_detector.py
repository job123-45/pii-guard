"""Contextual person-name detection with explicit model availability."""
from functools import lru_cache
import re

from ..models import Finding, Segment

MODEL_NAME = "en_core_web_sm"
NER_CONFIDENCE = 0.72
LABEL_CONFIDENCE = 0.82

_NAME_TOKEN = r"[A-Z][A-Za-z'’\-]*"
_LABELLED_NAME = re.compile(
    rf"(?i:\b(?P<label>name|contact)\b)(?:\s*[:#-]\s*|\s+)"
    rf"(?P<person>{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{1,3}})(?![\w])"
)
NON_PERSON_NAME_CONTEXT = {
    "task",
    "workflow",
    "rule",
    "trigger",
    "risk",
    "questionnaire",
    "vendor",
    "third-party",
}


@lru_cache(maxsize=1)
def _load_model():
    """Load the configured local spaCy model once; never download implicitly."""
    try:
        import spacy
    except ImportError:
        return None, "spaCy is not installed. Install project requirements."

    try:
        nlp = spacy.load(MODEL_NAME)
    except (OSError, ImportError) as exc:
        return (
            None,
            f"spaCy model {MODEL_NAME!r} is unavailable ({exc}). "
            f"Install it with: python -m spacy download {MODEL_NAME}",
        )

    if not nlp.has_pipe("ner"):
        return None, f"spaCy model {MODEL_NAME!r} does not include a named-entity recognizer."
    return nlp, None


def person_ner_status() -> tuple[bool, str]:
    """Return whether contextual PERSON NER is active and a user-safe explanation."""
    nlp, error = _load_model()
    if nlp is None:
        return False, error or f"spaCy model {MODEL_NAME!r} is unavailable."
    return True, f"spaCy {MODEL_NAME} loaded locally; PERSON entities are treated as candidates and require review."


def detect_labelled_names(segment: Segment) -> list[Finding]:
    """Keep the original Name:/Contact: pattern as a separate detection route."""
    findings = []
    for match in _LABELLED_NAME.finditer(segment.text):
        label_start = match.start("label")
        previous = re.search(r"([\w-]+)\s*$", segment.text[:label_start])
        if match.group("label").casefold() == "name" and previous:
            if previous.group(1).casefold() in NON_PERSON_NAME_CONTEXT:
                continue

        start, end = match.span("person")
        value = segment.text[start:end]
        findings.append(
            Finding(
                "PERSON",
                value,
                LABEL_CONFIDENCE,
                "context-label",
                segment.filename,
                segment.location,
                start,
                end,
                True,
            )
        )
    return findings


def detect_contextual(segment: Segment) -> list[Finding]:
    """Find labelled names and casual PERSON mentions with exact source offsets.

    spaCy detections are candidates, not verified identities. They always require
    human review. If the model is missing, labelled-name detection still works;
    callers must check :func:`person_ner_status` before releasing any payload.
    """
    candidates = detect_labelled_names(segment)
    nlp, _ = _load_model()
    if nlp is None:
        return candidates

    doc = nlp(segment.text)
    for entity in doc.ents:
        if entity.label_ != "PERSON":
            continue
        start, end = entity.start_char, entity.end_char
        if start < 0 or end <= start or end > len(segment.text):
            continue
        candidates.append(
            Finding(
                "PERSON",
                segment.text[start:end],
                NER_CONFIDENCE,
                f"spacy-ner:{MODEL_NAME}",
                segment.filename,
                segment.location,
                start,
                end,
                True,
            )
        )
    return candidates
