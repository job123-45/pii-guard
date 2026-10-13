# Optiv PII Guard QA report

**Run date:** 2026-10-13
**Environment:** Windows, Python virtual environment, Tesseract OCR 5.4.0

## Results at a glance

- Automated tests: **25 passed, 0 failed** (unit, source-document integration, fail-closed gateway, and Streamlit AppTest checks).
- Supplied source files processed with the actual Tesseract executable: **3 documents, 732 segments**.
- Scanned policy: **35/35 pages** produced non-empty OCR text. The shortest page had 958 characters. The configured page floor is 30 characters.
- Detection: **277 candidate findings** (189 email, 70 phone, 16 person, 1 government ID, 1 employee ID). The candidates have not been manually adjudicated.
- Redaction: **277/277** detected original values absent from their sanitized source segments, with the expected replacement present.
- Gateway: **BLOCK** with an empty eligible payload. The PowerPoint has 9 embedded image occurrences and the Word file has 41 embedded images; the app does not OCR Office images. Findings also await review.
- Labelled fixture: TP=7, FP=0, FN=0, TN=4; precision=100%, recall=100%, F1=100% on 11 synthetic cases only.
- Sample-document accuracy: **not measured**. The complete 732-segment annotation queue is ready for human labels; sample FP/FN and precision/recall must remain unknown until that review is complete.
- Presentation: 10 slides rendered to PNG and visually inspected. Artifact Tool import/export and final package/layout checks passed with zero findings.

## Test coverage and outcomes

The suite exercises:

- The actual supplied DOCX, PPTX, and scanned PDF extraction paths, source locations, office embedded-image notices, and segment redaction assertions.
- PDF OCR missing, exception, empty output, and output below the 30-character floor. Each state marks the real scanned policy page failed or uncertain and causes a gateway block.
- Corrupt-file extraction, detector disabled, detector exception, validation failure, and unresolved human findings. Each blocks and returns no eligible payload.
- A synthetic TXT file that moves from BLOCK to ALLOW after its person-name review is confirmed. The UI test confirms all detected values are absent from the simulated payload and that the sanitized download control enables only after approval.
- Audit JSON/CSV masking, span replacement, context-regression tests, and metrics formulas.

The standard integration suite stubs OCR output to keep repeat test runs deterministic. Separately, `docs/export_sample_annotation_queue.py` ran the full sample set through installed Tesseract. That real OCR run took 100.06 seconds and recorded 35 successful PDF pages.

## Measured sample run

| File | Extracted segments | Result |
|---|---:|---|
| Cadence Financial Group Organizational Pack (PPTX) | 184 | Text and tables extracted; 9 embedded image occurrences remain unresolved |
| Cadence Group Risk Management Policy v6.0 (PDF) | 35 pages | Tesseract OCR succeeded on 35/35 pages; 958–4,838 characters per page |
| Cadence TPRM Training (DOCX) | 513 | Paragraphs and table rows extracted; 41 embedded images remain unresolved |

All 732 extracted segments had non-empty text and status `ok` in this measured run. The 10 extraction notices refer to unresolved Office image content: nine PowerPoint image occurrences and one Word notice for 41 embedded images. This image gap keeps extraction incomplete and the gateway blocked.

The 277 detected findings consist of 189 EMAIL, 70 PHONE, 16 PERSON, 1 GOVERNMENT_ID, and 1 EMPLOYEE_ID. Automated redaction checks passed for every finding. This verifies replacement behavior for detected spans; it does not prove detector completeness or sample-document safety.

## Ground truth and metrics

`outputs/ground_truth_fixture.csv` is a manually specified, human-reviewable synthetic fixture with 11 examples: 7 positive and 4 negative. `outputs/labelled_fixture_case_results.csv` and `outputs/labelled_fixture_metrics.json` contain the executed predictions and confusion counts:

| TP | FP | FN | TN | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|---:|
| 7 | 0 | 0 | 4 | 100% | 100% | 100% |

These scores apply only to those small synthetic cases, which were designed around known rule behavior. They are not a performance estimate for the three supplied files.

`outputs/sample_document_annotation_queue.csv` contains one row for each of the 732 extracted source segments, source text, extraction status, predicted spans, and blank fields for gold labels, reviewer, and notes. Sample-document precision, recall, F1, false positives, and false negatives are **not available** until a reviewer fills the gold labels and the dataset is independently checked. The queue contains source text and detected original values; keep it local and restrict access.

## Browser and download checks

- Streamlit health endpoint returned HTTP 200 on port 8508.
- Streamlit AppTest uploaded the synthetic TXT file, displayed findings, confirmed the pending-review block, moved to ALLOW after review, and checked sanitized output and download-control states. Audit JSON/CSV controls remained available; the sanitized download stayed disabled until ALLOW.
- The in-app browser loaded the local Streamlit page and exposed the upload control. The current browser-control surface could not attach a file through its native file picker, so browser-level file upload and actual browser download completion remain unverified. No claim of those browser actions is made.

## PowerPoint visual validation

The existing 10-slide deck was edited in place through Artifact Tool import/export, rendered as 10 PNGs, and visually inspected slide by slide. The finalizer confirmed 10 slides, package integrity, exact source canvas dimensions, and zero layout findings. This is Artifact Tool render validation; the deck was not opened in PowerPoint for a separate native-app check.

## Remaining limits

- PPTX/DOCX embedded images are flagged but not OCRed. Until image content is extracted or a reviewer establishes it is irrelevant, the sample batch stays blocked.
- Rule-based detection covers limited identifiers and context-labeled names/addresses. No sample-document accuracy should be inferred from the synthetic fixture.
- Redaction exports sanitized extracted text, not format-preserving edits to the original source documents.

## Reproduction commands

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe docs\evaluate_labelled.py
.\.venv\Scripts\python.exe docs\export_sample_annotation_queue.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```
