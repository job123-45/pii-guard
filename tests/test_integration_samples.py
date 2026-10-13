from pathlib import Path
import pytest
from pii_guard.pipeline import extract_file,process_uploads
from pii_guard.extractors import pdf_extractor
import pymupdf as fitz

def first_page_pdf(path):
    source=fitz.open(path); single=fitz.open()
    single.insert_pdf(source,from_page=0,to_page=0)
    payload=single.tobytes()
    single.close(); source.close()
    return payload

ROOT=Path(__file__).resolve().parents[1]
SAMPLE_DIR=ROOT/"sample_inputs"
SAMPLES_AVAILABLE=all((SAMPLE_DIR/name).is_file() for name in [
    "Cadence_TPRM_Training.docx",
    "Cadence_Financial_Group_Organizational_Pack.pptx",
    "Cadence_Group_Risk_Management_Policy__v6.0.pdf",
])

def require_sample(name):
    path=SAMPLE_DIR/name
    if not path.is_file():
        pytest.skip(f"Supplied sample {name} is not present; obtain it through approved team storage")
    return path

@pytest.mark.parametrize("name",["Cadence_TPRM_Training.docx","Cadence_Financial_Group_Organizational_Pack.pptx"])
def test_office_sample_extraction(name):
    p=require_sample(name)
    segments,errors=extract_file(name,p.read_bytes())
    assert segments and all(s.filename==name for s in segments)
    if name.endswith(".pptx"):
        assert any("embedded image detected" in error for error in errors)
    if name.endswith(".docx"):
        assert any("embedded image(s) detected" in error for error in errors)

def test_policy_pdf_extraction():
    p=require_sample("Cadence_Group_Risk_Management_Policy__v6.0.pdf")
    # Mock OCR for this structural test. Real OCR runs in the all-samples test.
    original=pdf_extractor.image_to_text
    pdf_extractor.image_to_text=lambda image: "Policy page extracted by test OCR. "*4
    try: segments,errors=extract_file(p.name,p.read_bytes())
    finally: pdf_extractor.image_to_text=original
    assert segments
    assert len(segments)==35
    assert all(s.location.startswith("page:") for s in segments)
    assert all(s.status in {"ok","uncertain","failed"} for s in segments)
    assert all(s.status!="ok" or bool(s.text.strip()) for s in segments)

@pytest.mark.parametrize("mock_ocr, expected_status, expected_notice",[
    (lambda _image: "", "uncertain", "OCR completed without extracting text"),
    (lambda _image: "short", "uncertain", "OCR extracted only 5 character(s)"),
    (lambda _image: (_ for _ in ()).throw(RuntimeError("synthetic OCR crash")), "failed", "OCR failed: synthetic OCR crash"),
])
def test_real_scanned_pdf_page_blocks_empty_or_failed_ocr(monkeypatch,mock_ocr,expected_status,expected_notice):
    p=require_sample("Cadence_Group_Risk_Management_Policy__v6.0.pdf")
    monkeypatch.setattr(pdf_extractor,"ocr_available",lambda: True)
    monkeypatch.setattr(pdf_extractor,"image_to_text",mock_ocr)
    segments,errors=pdf_extractor.extract_pdf(p.name,first_page_pdf(p))
    assert segments[0].status==expected_status
    assert any(expected_notice in error for error in errors)

def test_real_scanned_pdf_page_blocks_when_ocr_is_missing(monkeypatch):
    p=require_sample("Cadence_Group_Risk_Management_Policy__v6.0.pdf")
    monkeypatch.setattr(pdf_extractor,"ocr_available",lambda: False)
    segments,errors=pdf_extractor.extract_pdf(p.name,first_page_pdf(p))
    assert segments[0].status=="failed"
    assert any("OCR required but Tesseract OCR executable is unavailable" in error for error in errors)

def test_all_samples_redact_detected_values_and_fail_closed(monkeypatch):
    # Keep the integration suite fast and deterministic. The report's separate
    # real-sample run exercises the installed Tesseract binary on every page.
    monkeypatch.setattr(pdf_extractor,"ocr_available",lambda: True)
    monkeypatch.setattr(pdf_extractor,"image_to_text",lambda _image: "Policy page OCR integration fixture text."*2)
    if not SAMPLES_AVAILABLE:
        pytest.skip("Supplied sample documents are not present; obtain them through approved team storage")
    files=[(p.name,p.read_bytes()) for p in sorted(SAMPLE_DIR.iterdir()) if p.is_file()]
    segments,findings,redacted,gateway,errors=process_uploads(files)
    assert len(segments)==732
    assert findings and errors
    assert not gateway.allowed and gateway.sanitized_text==""
    sanitized={(s.filename,s.location):text for s,text in redacted}
    for f in findings:
        text=sanitized[(f.filename,f.location)]
        assert f.value not in text
        assert f"[REDACTED_{f.entity_type}]" in text

def test_synthetic_demo_is_sanitized_and_allowed_after_review():
    p=ROOT/"tests"/"fixtures"/"Synthetic_Demo.txt"
    segments,findings,redacted,gateway,errors=process_uploads([(p.name,p.read_bytes())])
    assert findings and not errors
    assert not gateway.allowed  # The labelled person is awaiting review.
    for f in findings:
        f.reviewed=True
    from pii_guard.gateway import decide_gateway
    sanitized={(s.filename,s.location):text for s,text in redacted}
    text=sanitized[(segments[0].filename,segments[0].location)]
    assert all(f.value not in text for f in findings)
    approved=decide_gateway(segments,findings,text,errors)
    assert approved.allowed and approved.sanitized_text==text
