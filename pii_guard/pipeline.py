from pathlib import Path
from .models import Segment, Finding
from .validators import validate_upload
from .detection.pii_engine import detect_pii
from .redaction.text_redactor import redact_text
from .gateway import decide_gateway, GatewayDecision
from .extractors.pdf_extractor import extract_pdf
from .extractors.docx_extractor import extract_docx
from .extractors.pptx_extractor import extract_pptx

def extract_file(filename: str, content: bytes) -> tuple[list[Segment],list[str]]:
    valid,message=validate_upload(filename,len(content),content)
    if not valid: raise ValueError(message)
    suffix=Path(filename).suffix.lower()
    if suffix==".pdf": return extract_pdf(filename,content)
    if suffix==".docx": return extract_docx(filename,content)
    if suffix==".pptx": return extract_pptx(filename,content)
    try: text=content.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise ValueError("TXT must be UTF-8 encoded.") from exc
    return [Segment(filename,"text:1","utf-8",text,"ok",not bool(text.strip()))],([] if text.strip() else ["Empty text content."])

def process_uploads(files: list[tuple[str,bytes]], detection_ok: bool=True, validation_ok: bool=True):
    segments=[]; errors=[]
    for name,data in files:
        try:
            extracted,problems=extract_file(name,data); segments.extend(extracted); errors.extend(f"{name}: {e}" for e in problems)
        except Exception as exc:
            errors.append(f"{name}: extraction failed: {exc}")
            segments.append(Segment(name,"file","failed","","failed",True))
    if detection_ok:
        try:
            findings=detect_pii(segments)
        except Exception as exc:
            errors.append(f"PII detection failed: {exc}")
            detection_ok=False
            findings=[]
    else:
        findings=[]
    redacted=[]
    for seg in segments:
        fs=[f for f in findings if f.filename==seg.filename and f.location==seg.location]
        decisions={(f.filename,f.start,f.end):f.reviewed for f in fs}
        redacted.append((seg,redact_text(seg.text,fs,decisions)))
    output="\n\n".join(f"[{s.filename} | {s.location}]\n{t}" for s,t in redacted if s.status=="ok")
    gateway=decide_gateway(segments,findings,output,errors,detection_ok,validation_ok)
    return segments,findings,redacted,gateway,errors
