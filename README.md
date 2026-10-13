# Optiv PII Guard

Local-first Streamlit prototype for extracting documents, identifying common PII patterns, producing a sanitized text view, and blocking simulated downstream AI handoff when processing is incomplete.

## Setup

Requires Python 3.11+ and (for scanned PDF OCR) Tesseract OCR 5.x. The app checks `TESSERACT_CMD`, then `PATH`, then the standard Windows installation directory `C:\Program Files\Tesseract-OCR\tesseract.exe`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Install the English person-name model used for contextual NER
python -m spacy download en_core_web_sm
# Confirm that the local model can be loaded
python -c "import spacy; spacy.load('en_core_web_sm'); print('NER model ready')"
streamlit run app.py
```

spaCy and its language model are separate setup steps. The application does not
download models implicitly. The sidebar reports whether `en_core_web_sm` is
available. If it is missing, contextual person-name detection is unavailable and
the privacy gateway blocks release; existing labelled-name and pattern findings
are still redacted in the prepared text.

Install Tesseract separately and add its executable to PATH (Windows: `winget install --id UB-Mannheim.TesseractOCR --exact`; macOS: `brew install tesseract`; Debian/Ubuntu: `sudo apt-get install tesseract-ocr`). Restart the terminal and verify with `tesseract --version`. OCR runs locally; OCR failure blocks gateway release.

Run checks with `python -m pytest -q`. The provided Python environment may require installation of the project dependencies first.

## Features and limitations

- PDF: PyMuPDF text extraction, page traceability, low-text/image pages sent to local Tesseract OCR. Missing OCR, OCR exceptions, empty OCR, and OCR output below 30 characters mark the page failed or uncertain and block release.
- DOCX: paragraphs and tables; embedded images are flagged for manual review.
- PPTX: text shapes and tables; image shapes are flagged for manual review.
- TXT: UTF-8 extraction.
- Detectors cover email, phone, labeled employee/account/government IDs, addresses, explicitly labeled names, and contextual `PERSON` entities from spaCy `en_core_web_sm`. NER hits are candidates and always require human review. A name model is imperfect: it can miss names and can mark non-name text as a person, so an empty finding list is not evidence that a document contains no names.
- Redaction is applied to extracted text only. Source PDF/DOCX/PPTX files are not rewritten. Use sanitized text export, and do not treat it as source-document sanitization.
- No original text is sent to an external model. “Allow” represents only a simulated handoff of sanitized text.
- An empty findings list is not proof of absence of PII.

The supplied policy PDF completed OCR on all 35 pages in the 2026-10-13 QA run. The supplied PowerPoint and Word document each contain embedded images that this version does not OCR; these remain explicit extraction notices and keep the gateway blocked. Sample-document detection labels remain pending manual adjudication. The supplied source documents are intentionally excluded from this repository because they contain source text; obtain them through your approved team storage and place them in `sample_inputs/` to run the source-document integration checks. Those checks skip with an explicit reason if a required sample is unavailable; synthetic and unit tests still run.

## QA and sample run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe docs\evaluate_labelled.py
.\.venv\Scripts\python.exe docs\export_sample_annotation_queue.py
```

The evaluator scores only the 11-case synthetic fixture. `outputs\sample_document_annotation_queue.csv` contains all extracted sample segments and predicted spans with blank gold labels. It includes original document text and detected values for human review, so keep it local and do not share it outside the approved review process. Do not use the synthetic fixture scores as sample-document accuracy.

## Project layout

`pii_guard/` contains extraction, detection, redaction, reporting and gateway modules. `docs/` contains the design and test notes. Supplied reference material is in `sample_inputs/`; generated exports go in `outputs/`.
