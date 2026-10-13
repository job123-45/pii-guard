import os
import shutil
from pathlib import Path
from PIL import Image
import pytesseract

def tesseract_executable() -> str | None:
    configured=os.environ.get("TESSERACT_CMD")
    if configured and Path(configured).is_file():
        return configured
    on_path=shutil.which("tesseract")
    if on_path:
        return on_path
    program_files=os.environ.get("ProgramFiles",r"C:\Program Files")
    common=Path(program_files)/"Tesseract-OCR"/"tesseract.exe"
    return str(common) if common.is_file() else None

def ocr_available() -> bool:
    return tesseract_executable() is not None

def image_to_text(image: Image.Image) -> str:
    executable=tesseract_executable()
    if not executable: raise RuntimeError("Tesseract OCR executable is unavailable. Set TESSERACT_CMD or add Tesseract to PATH.")
    pytesseract.pytesseract.tesseract_cmd=executable
    return pytesseract.image_to_string(image)
