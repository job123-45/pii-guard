"""Source-document redaction boundary: unsupported formats fail closed."""
from pathlib import Path
from .text_redactor import redact_text
from ..models import Finding

def redact_document(filename: str, content: bytes, findings: list[Finding]) -> tuple[str,bytes]:
    """Return a safe text export; never labels extracted text as a sanitized source file."""
    if Path(filename).suffix.lower() != ".txt":
        raise NotImplementedError("Safe structure-preserving export is not available for this format; use the clearly labelled sanitized text export.")
    text=content.decode("utf-8-sig")
    return "sanitized_text",redact_text(text,findings)
