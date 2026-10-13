import io
import pymupdf as fitz
from PIL import Image
from .ocr_engine import image_to_text, ocr_available
from ..models import Segment
from ..config import OCR_MIN_CHARS_PER_PAGE

def extract_pdf(filename: str, content: bytes) -> tuple[list[Segment],list[str]]:
    doc=fitz.open(stream=content,filetype="pdf"); segments=[]; errors=[]
    for i,page in enumerate(doc):
        text=page.get_text("text").strip(); method="pymupdf"
        if len(text)<OCR_MIN_CHARS_PER_PAGE and page.get_images(full=True):
            if not ocr_available():
                message=f"Page {i+1}: OCR required but Tesseract OCR executable is unavailable. Install Tesseract and add it to PATH."
                errors.append(message)
                segments.append(Segment(filename,f"page:{i+1}","ocr-unavailable",text,"failed",True)); continue
            try:
                pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
                text=image_to_text(Image.open(io.BytesIO(pix.tobytes("png")))).strip(); method="tesseract-ocr"
            except Exception as exc:
                errors.append(f"Page {i+1}: OCR failed: {exc}")
                segments.append(Segment(filename,f"page:{i+1}","ocr-failed",text,"failed",True)); continue
            if not text:
                message=f"Page {i+1}: OCR completed without extracting text; scanned page remains unresolved."
                errors.append(message)
                segments.append(Segment(filename,f"page:{i+1}","ocr-empty","","uncertain",True)); continue
            if len(text)<OCR_MIN_CHARS_PER_PAGE:
                message=f"Page {i+1}: OCR extracted only {len(text)} character(s); below the {OCR_MIN_CHARS_PER_PAGE}-character threshold, page remains uncertain."
                errors.append(message)
                segments.append(Segment(filename,f"page:{i+1}","tesseract-ocr-low-text",text,"uncertain",True)); continue
        elif len(text)<OCR_MIN_CHARS_PER_PAGE:
            errors.append(f"Page {i+1}: little or no extractable text; no embedded image detected for OCR.")
            segments.append(Segment(filename,f"page:{i+1}",method,text,"uncertain",True)); continue
        segments.append(Segment(filename,f"page:{i+1}",method,text,"ok",method=="tesseract-ocr"))
    return segments,errors
