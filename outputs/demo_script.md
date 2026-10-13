# Live demo script

## Start the app

From the project root, run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. The app auto-detects Tesseract through `TESSERACT_CMD`, `PATH`, or `C:\Program Files\Tesseract-OCR\tesseract.exe`.

## Allow path: reviewed synthetic document

1. Upload `tests\fixtures\Synthetic_Demo.txt`. It contains fabricated values for a local demo.
2. Point out that findings appear with values hidden. The labeled person name requires review, so the gateway initially shows **BLOCK**.
3. In **Human review**, confirm the `PERSON` row. The gateway should change to **ALLOW**.
4. Show the exact simulated payload. Each detected value should appear as a category placeholder; no original finding should remain.
5. Download sanitized text and the JSON/CSV audit reports. The audit values remain masked by default.

## Block path: validation failure

1. Keep the synthetic file uploaded and the person finding confirmed.
2. Select **Simulate validation failure** in the sidebar.
3. Confirm **BLOCK** and the empty eligible payload. Clear the toggle to restore the reviewed allow state.

## Block path: supplied documents

Upload these together from `sample_inputs`:

- `Cadence_Group_Risk_Management_Policy__v6.0.pdf`
- `Cadence_Financial_Group_Organizational_Pack.pptx`
- `Cadence_TPRM_Training.docx`

Then show:

1. **732 extracted segments** across the three files: 35 PDF pages, 184 PPTX segments, and 513 DOCX paragraph/table segments.
2. Expand **PDF page extraction status**. In the measured run, Tesseract 5.4 extracted non-empty text on all **35/35** policy pages; page text lengths ranged from 958 to 4,838 characters, above the configured 30-character floor.
3. Expand extraction notices. The app found nine PowerPoint image occurrences and one Word notice covering 41 embedded images. Office embedded-image OCR is not implemented, so this unresolved content blocks release.
4. Show **277 unadjudicated candidate findings** and the **BLOCK** gateway state. All 277 detected values were absent from their sanitized source segments and each expected replacement was present. The block means no payload is eligible.

Do not approve the sample batch as safe. The findings have no sample-document ground-truth labels, and Office image content remains unresolved.

## Measured evaluation and QA commands

The synthetic fixture has 11 hand-authored labelled cases: 7 positives and 4 negatives. Its measured score is TP=7, FP=0, FN=0, TN=4, precision=100%, recall=100%, F1=100%. These fixture results do not describe accuracy on the supplied documents.

The full sample annotation queue is `outputs\sample_document_annotation_queue.csv`. It includes original extracted segment text and candidate spans for review; keep it local. Human labels are blank. Sample-document precision, recall, F1, FP and FN remain unmeasured until a reviewer completes the annotations.

Run the test suite and fixture evaluator:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe docs\evaluate_labelled.py
```

To rerun all three source files through installed Tesseract and refresh the annotation queue and sample metrics (about 100 seconds on the QA machine):

```powershell
.\.venv\Scripts\python.exe docs\export_sample_annotation_queue.py
```

## Automation scope

Streamlit AppTest verified synthetic file upload, findings/review state, the sanitized allow payload, and download button availability. The localhost app and upload control were visible in the browser, but this browser-control interface could not attach a file through the native file picker. No real-browser download or browser-upload completion is claimed.
