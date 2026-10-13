import pytest

from pii_guard.detection.ner_detector import person_ner_status
from pii_guard.detection.pii_engine import detect_pii
from pii_guard.models import Segment
from pii_guard.pipeline import process_uploads
from pii_guard.redaction.text_redactor import redact_text


@pytest.fixture
def require_ner():
    available, message = person_ner_status()
    if not available:
        pytest.skip(message)


def segment(text):
    return Segment("ner.txt", "text:1", "utf-8", text)


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("Rahul Sharma prepared the report.", "Rahul Sharma"),
        ("The document was reviewed by Priya Mehta.", "Priya Mehta"),
    ],
)
def test_casual_person_mentions_have_exact_offsets_and_require_review(text, name, require_ner):
    findings = [f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON"]
    assert len(findings) == 1
    finding = findings[0]
    start = text.index(name)
    assert (finding.value, finding.start, finding.end) == (name, start, start + len(name))
    assert finding.review_required and not finding.reviewed
    assert finding.method.startswith("spacy-ner:")


def test_labelled_name_rules_are_preserved_and_duplicates_collapsed(require_ner):
    text = "Name: Jane Doe. Contact: John Smith."
    findings = [f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON"]
    assert [(f.value, f.start, f.end) for f in findings] == [
        ("Jane Doe", text.index("Jane Doe"), text.index("Jane Doe") + len("Jane Doe")),
        ("John Smith", text.index("John Smith"), text.index("John Smith") + len("John Smith")),
    ]


def test_sentence_without_person_name_has_no_person_finding(require_ner):
    text = "The quarterly report was reviewed by the audit team on Monday."
    assert not [f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON"]


def test_multiple_person_names_in_one_sentence_are_found(require_ner):
    text = "Rahul Sharma briefed Priya Mehta before the meeting."
    findings = [f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON"]
    assert [f.value for f in findings] == ["Rahul Sharma", "Priya Mehta"]
    assert all(text[f.start:f.end] == f.value for f in findings)


@pytest.mark.parametrize(
    "text",
    [
        "The risk management workflow triggered a questionnaire for the vendor on Monday.",
        "The report covers legal risk, vendor review and task workflow.",
    ],
)
def test_common_non_person_terms_are_not_person_findings(text, require_ner):
    assert not [f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON"]


def test_redaction_removes_each_detected_name_and_keeps_replacements(require_ner):
    text = "Rahul Sharma prepared the report, and Priya Mehta reviewed it."
    findings = [f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON"]
    sanitized = redact_text(text, findings)
    assert findings
    for finding in findings:
        assert finding.value not in sanitized
        assert sanitized.count("[REDACTED_PERSON]") >= len(findings)


def test_redaction_removes_repeated_original_value_from_entire_segment():
    text = "Rahul Sharma prepared the report; Rahul Sharma approved it."
    finding = next(f for f in detect_pii([segment(text)]) if f.entity_type == "PERSON")
    sanitized = redact_text(text, [finding])
    assert "Rahul Sharma" not in sanitized
    assert sanitized.count("[REDACTED_PERSON]") == 2


def test_missing_model_is_explicit_and_gateway_fails_closed(monkeypatch):
    import pii_guard.detection.ner_detector as ner_detector

    monkeypatch.setattr(ner_detector, "_load_model", lambda: (None, "model is not installed"))
    segments, findings, redacted, gateway, errors = process_uploads(
        [("missing.txt", b"Contact Jane Doe at jane@example.com")]
    )
    assert any("Contextual person-name NER unavailable" in error for error in errors)
    assert not gateway.allowed and gateway.sanitized_text == ""
    assert any(f.entity_type == "PERSON" and f.value == "Jane Doe" for f in findings)
    prepared = redacted[0][1]
    assert "Jane Doe" not in prepared and "jane@example.com" not in prepared
    assert "[REDACTED_PERSON]" in prepared and "[REDACTED_EMAIL]" in prepared
