from dataclasses import dataclass
from .models import Segment, Finding

@dataclass
class GatewayDecision:
    allowed: bool
    reasons: list[str]
    sanitized_text: str

def decide_gateway(segments: list[Segment], findings: list[Finding], sanitized_text: str, extraction_errors: list[str], detection_ok: bool=True, validation_ok: bool=True) -> GatewayDecision:
    reasons=[]
    if extraction_errors or any(s.status!="ok" for s in segments): reasons.append("Extraction, OCR, or processing is incomplete/uncertain.")
    if not detection_ok: reasons.append("PII detection failed.")
    if not validation_ok: reasons.append("Required validation failed.")
    if any(f.review_required and not f.reviewed for f in findings): reasons.append("PII findings require human review.")
    if not sanitized_text and any(s.text for s in segments): reasons.append("Sanitized output is empty despite extracted source text.")
    return GatewayDecision(not reasons,reasons,sanitized_text if not reasons else "")
