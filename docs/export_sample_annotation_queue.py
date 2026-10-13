"""Run all supplied samples locally and export a human annotation queue + measured QA summary."""
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pii_guard.pipeline import process_uploads
from pii_guard.extractors.ocr_engine import ocr_available,tesseract_executable
from pii_guard.config import OCR_MIN_CHARS_PER_PAGE

OUT=ROOT/"outputs"
FILES=[(p.name,p.read_bytes()) for p in sorted((ROOT/"sample_inputs").iterdir()) if p.suffix.lower() in {".pdf",".pptx",".docx"}]
started=time.perf_counter()
segments,findings,redacted,gateway,errors=process_uploads(FILES)
elapsed=round(time.perf_counter()-started,2)
redacted_by_key={(s.filename,s.location):text for s,text in redacted}
redaction_rows=[]
for finding in findings:
    text=redacted_by_key[(finding.filename,finding.location)]
    replacement=f"[REDACTED_{finding.entity_type}]"
    redaction_rows.append({"source":finding.filename,"location":finding.location,"entity_type":finding.entity_type,
                          "original_absent":finding.value not in text,"replacement_present":replacement in text})

rows=[]
for i,segment in enumerate(segments,1):
    segment_findings=[f for f in findings if f.filename==segment.filename and f.location==segment.location]
    rows.append({"segment_id":f"SEG-{i:04d}","source_document":segment.filename,"location":segment.location,
                 "extraction_method":segment.method,"extraction_status":segment.status,"source_text_for_review":segment.text,
                 "predicted_entities_json":json.dumps([{"type":f.entity_type,"value":f.value,"start":f.start,"end":f.end} for f in segment_findings],ensure_ascii=False),
                 "human_review_status":"PENDING","gold_entities_json":"","reviewer":"","review_notes":""})
OUT.mkdir(exist_ok=True)
with (OUT/"sample_document_annotation_queue.csv").open("w",newline="",encoding="utf-8-sig") as stream:
    writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

by_doc=Counter(s.filename for s in segments)
status_counts={}
for filename in sorted({s.filename for s in segments}):
    status_counts[filename]=dict(Counter(s.status for s in segments if s.filename==filename))
pdf_pages=[s for s in segments if s.filename.lower().endswith(".pdf")]
ocr_pages=[s for s in pdf_pages if s.method.startswith("ocr-") or s.method=="tesseract-ocr"]
summary={"documents":len(FILES),"segments_extracted":len(segments),"segments_by_document":dict(by_doc),
         "page_or_segment_status_by_document":status_counts,"pdf_pages_total":len(pdf_pages),
         "pdf_ocr_pages":len(ocr_pages),"pdf_ocr_status_counts":dict(Counter(s.status for s in ocr_pages)),
         "ocr_min_chars_per_page":OCR_MIN_CHARS_PER_PAGE,
         "pdf_ocr_pages_detail":[{"page":s.location,"method":s.method,"status":s.status,"characters":len(s.text)} for s in pdf_pages],
         "tesseract_available":ocr_available(),"tesseract_executable":tesseract_executable(),
         "extraction_notices":len(errors),"extraction_notice_text":errors,
         "findings_total":len(findings),"findings_by_category":dict(Counter(f.entity_type for f in findings)),
         "findings_manual_adjudication":"PENDING; see sample_document_annotation_queue.csv",
         "redaction_checks_total":len(redaction_rows),"detected_value_absent_checks_passed":sum(r["original_absent"] for r in redaction_rows),
         "replacement_present_checks_passed":sum(r["replacement_present"] for r in redaction_rows),
         "all_detected_values_absent":all(r["original_absent"] for r in redaction_rows),
         "all_replacements_present":all(r["replacement_present"] for r in redaction_rows),
         "gateway_allowed":gateway.allowed,"gateway_reasons":gateway.reasons,
         "gateway_payload_empty_on_block":not gateway.allowed and gateway.sanitized_text=="",
         "elapsed_seconds":elapsed}
(OUT/"sample_integration_metrics.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in summary.items() if k!="extraction_notice_text"},indent=2))
