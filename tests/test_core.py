from pii_guard.models import Segment, Finding
from pii_guard.detection.pii_engine import detect_pii
from pii_guard.redaction.text_redactor import redact_text
from pii_guard.validators import validate_upload
from pii_guard.gateway import decide_gateway
from pii_guard.metrics import score_predictions,structure_retention
from pii_guard.pipeline import process_uploads
from pii_guard.reporting import audit_json,audit_csv

def test_detect_email_phone_and_references():
    s=Segment("x.txt","text:1","utf-8","Contact Jane Doe at jane@example.com or 212-555-0198")
    fs=detect_pii([s]); assert {f.entity_type for f in fs}=={"PERSON","EMAIL","PHONE"}
    assert all(f.filename=="x.txt" and f.location=="text:1" for f in fs)

def test_task_name_is_not_classified_as_person():
    fs=detect_pii([Segment("x.txt","text:1","utf-8","Task Name: Legal Risk Identified")])
    assert not any(f.entity_type=="PERSON" for f in fs)

def test_redact_offsets_right_to_left():
    s=Segment("x.txt","text:1","utf-8","a@b.com and c@d.com")
    fs=detect_pii([s]); result=redact_text(s.text,fs)
    assert result=="[REDACTED_EMAIL] and [REDACTED_EMAIL]"

def test_identifier_redaction_preserves_label_context():
    s=Segment("x.txt","text:1","utf-8","Employee ID: EMP-12345")
    fs=detect_pii([s]); assert len(fs)==1 and fs[0].value=="EMP-12345"
    assert redact_text(s.text,fs)=="Employee ID: [REDACTED_EMPLOYEE_ID]"

def test_employee_identifier_prose_is_not_an_employee_id():
    fs=detect_pii([Segment("x.txt","text:1","utf-8","employee identifiers, employee identification and employee IDs are discussed")])
    assert not any(f.entity_type=="EMPLOYEE_ID" for f in fs)

def test_overlapping_entities_deduplicated():
    fs=detect_pii([Segment("x.txt","p1","utf-8","Employee ID: EMP-12345")])
    assert len(fs)==1

def test_upload_validation():
    assert validate_upload("ok.txt",2,b"hi")[0]
    assert not validate_upload("empty.txt",0,b"")[0]
    assert not validate_upload("bad.pdf",4,b"nope")[0]

def test_gateway_fail_closed():
    s=Segment("x.txt","text:1","utf-8","text")
    decision=decide_gateway([s],[],"text",["OCR failed"])
    assert not decision.allowed and decision.sanitized_text==""
    review=Finding("PERSON","Jane Doe",.7,"ner","x.txt","text:1",0,8,True)
    assert not decide_gateway([s],[review],"[REDACTED]",[]).allowed
    review.reviewed=True
    assert decide_gateway([s],[review],"[REDACTED]",[]).allowed

def test_pending_review_is_still_redacted_before_gateway_block():
    s=Segment("x.txt","text:1","utf-8","Name: Jane Doe")
    finding=detect_pii([s])[0]
    assert finding.review_required and not finding.reviewed
    sanitized=redact_text(s.text,[finding])
    assert sanitized=="Name: [REDACTED_PERSON]"
    assert "Jane Doe" not in sanitized
    decision=decide_gateway([s],[finding],sanitized,[])
    assert not decision.allowed and decision.sanitized_text==""

def test_metrics_formulas():
    m=score_predictions({("EMAIL","a@b.com"),("PHONE","2125550198")},{("EMAIL","a@b.com"),("PERSON","Jane Doe")})
    assert (m["tp"],m["fp"],m["fn"],m["precision"],m["recall"],m["f1"])==(1,1,1,.5,.5,.5)
    assert structure_retention(4,4)==1

def test_corrupt_file_blocks_gateway():
    segments,findings,redacted,gateway,errors=process_uploads([("corrupt.pdf",b"%PDF not a valid document")])
    assert errors and not gateway.allowed and gateway.sanitized_text==""

def test_detector_failure_blocks_gateway():
    segments,findings,redacted,gateway,errors=process_uploads([("known.txt",b"Contact Jane Doe at jane@example.com")],detection_ok=False)
    assert segments and not findings
    assert errors==[]
    assert not gateway.allowed and gateway.sanitized_text==""
    assert "PII detection failed." in gateway.reasons

def test_detector_exception_is_caught_and_blocks_gateway(monkeypatch):
    import pii_guard.pipeline as pipeline
    monkeypatch.setattr(pipeline,"detect_pii",lambda _segments: (_ for _ in ()).throw(RuntimeError("synthetic detector crash")))
    segments,findings,redacted,gateway,errors=pipeline.process_uploads([("known.txt",b"Contact Jane Doe at jane@example.com")])
    assert segments and not findings
    assert any("PII detection failed: synthetic detector crash" in error for error in errors)
    assert not gateway.allowed and gateway.sanitized_text==""
    assert "PII detection failed." in gateway.reasons

def test_failed_validation_blocks_gateway():
    segments,findings,redacted,gateway,errors=process_uploads([("plain.txt",b"No detected value")],validation_ok=False)
    assert not gateway.allowed and gateway.sanitized_text==""
    assert "Required validation failed." in gateway.reasons

def test_audit_hides_values_by_default():
    f=Finding("EMAIL","private@example.com",.99,"regex","x.txt","text:1",0,18)
    assert "private@example.com" not in audit_json([f])
    assert "private@example.com" not in audit_csv([f])
    assert "private@example.com" in audit_json([f],reveal=True)
