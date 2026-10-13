from pathlib import Path
from .config import MAX_FILE_BYTES, SUPPORTED

def validate_upload(filename: str, size: int, content: bytes) -> tuple[bool,str]:
    suffix=Path(filename).suffix.lower()
    if suffix not in SUPPORTED: return False, "Unsupported file type. Use PDF, DOCX, PPTX or TXT."
    if size <= 0 or not content: return False, "Empty files cannot be processed."
    if size > MAX_FILE_BYTES: return False, "File exceeds 25 MiB limit."
    if suffix == ".pdf" and not content.startswith(b"%PDF"): return False, "Invalid PDF signature."
    if suffix in {".docx", ".pptx"} and not content.startswith(b"PK"): return False, "Invalid Office document container."
    return True, "Validated"
