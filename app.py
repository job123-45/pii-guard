from collections import Counter
import streamlit as st
import pandas as pd
import hashlib
from pii_guard.pipeline import process_uploads
from pii_guard.reporting import audit_csv,audit_json
from pii_guard.redaction.text_redactor import redact_text
from pii_guard.gateway import decide_gateway
from pii_guard.extractors.ocr_engine import ocr_available

def _mask_text(text, findings, filename, location):
    fs=[f for f in findings if f.filename==filename and f.location==location]
    return redact_text(text,fs,{(f.filename,f.start,f.end):True for f in fs})

st.set_page_config(page_title="Optiv PII Guard | Cadence",page_icon="🛡️",layout="wide")
st.markdown("""<style>
body {background:#f4f6f9} .stApp {background:#f4f6f9} h1,h2,h3 {color:#10233f}
div[data-testid="stMetric"] {background:white;padding:16px;border-radius:10px;border-left:4px solid #f58220}
.block-container {padding-top:2rem}
</style>""",unsafe_allow_html=True)
st.title("🛡️ Optiv PII Guard")
st.caption("Cadence Financial Group · Document privacy review and simulated AI gateway")
st.warning("A result with no detected findings does not prove a document contains no PII. Review output before use.")
uploads=st.file_uploader("Upload PDF, DOCX, PPTX or TXT documents",type=["pdf","docx","pptx","txt"],accept_multiple_files=True)
with st.sidebar:
    st.header("Review controls")
    reveal=st.checkbox("Reveal detected values",value=False,help="Sensitive source content may appear on screen.")
    if reveal: st.error("Sensitive values are visible in this session.")
    simulate_failure=st.checkbox("Simulate validation failure")
    st.caption("Local OCR engine: Tesseract available" if ocr_available() else "Local OCR engine: unavailable; scanned pages will block release")
if uploads:
    data=[(u.name,u.getvalue()) for u in uploads]
    with st.spinner("Extracting, scanning and redacting locally..."):
        segments,findings,redacted,gateway,errors=process_uploads(data,validation_ok=not simulate_failure)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Documents",len(uploads)); c2.metric("Text segments",len(segments)); c3.metric("PII findings",len(findings)); c4.metric("Review required",sum(f.review_required for f in findings))
    if errors:
        with st.expander("Extraction notices and failures",expanded=True):
            for e in errors: st.warning(e)
    pdf_pages=[s for s in segments if s.filename.lower().endswith(".pdf") and s.location.startswith("page:")]
    if pdf_pages:
        with st.expander("PDF page extraction status",expanded=False):
            status_counts=Counter(s.status for s in pdf_pages)
            st.caption(f"{status_counts.get('ok',0)} of {len(pdf_pages)} PDF pages have non-empty extracted text. Failed or uncertain pages block release.")
            st.dataframe(pd.DataFrame([{"Document":s.filename,"Page":s.location,"Method":s.method,"Status":s.status,"Characters":len(s.text)} for s in pdf_pages]),use_container_width=True,hide_index=True)
    st.subheader("Human review")
    review_rows=[]
    for i,f in enumerate(findings):
        review_rows.append({"Finding":i+1,"Category":f.entity_type,"Source":f.filename+" · "+f.location,"Confidence":f.confidence,"Value":f.value if reveal else "[HIDDEN]","Needs review":f.review_required,"Reviewer confirmed":f.reviewed})
    if review_rows:
        upload_fingerprint=hashlib.sha256(b"".join(content for _,content in data)).hexdigest()[:16]
        review_key="review_"+upload_fingerprint
        reviewed_df=st.data_editor(pd.DataFrame(review_rows),key=review_key,use_container_width=True,hide_index=True,disabled=["Finding","Category","Source","Confidence","Value","Needs review"],column_config={"Reviewer confirmed":st.column_config.CheckboxColumn("Reviewer confirmed",help="Confirm the detection is valid; the span will then be redacted before release." )})
        for i,f in enumerate(findings): f.reviewed=bool(reviewed_df.iloc[i]["Reviewer confirmed"])
        redacted=[]
        for seg in segments:
            fs=[f for f in findings if f.filename==seg.filename and f.location==seg.location]
            decisions={(f.filename,f.start,f.end):f.reviewed for f in fs}
            redacted.append((seg,redact_text(seg.text,fs,decisions)))
        sanitized="\n\n".join(f"[{s.filename} | {s.location}]\n{t}" for s,t in redacted if s.status=="ok")
        gateway=decide_gateway(segments,findings,sanitized,errors,True,not simulate_failure)
    status=st.success if gateway.allowed else st.error
    status("AI gateway ALLOW — simulated sanitized handoff only." if gateway.allowed else "AI gateway BLOCK — " + " ".join(gateway.reasons))
    left,right=st.columns(2)
    with left:
        st.subheader("PII findings")
        types=sorted({f.entity_type for f in findings}); chosen=st.multiselect("Categories",types,default=types)
        view=[f.public_dict(reveal) for f in findings if f.entity_type in chosen]
        st.dataframe(pd.DataFrame(view),use_container_width=True,hide_index=True)
    with right:
        st.subheader("Document summary")
        counts=Counter(f.entity_type for f in findings)
        st.dataframe(pd.DataFrame([{"Category":k,"Count":v} for k,v in sorted(counts.items())]),use_container_width=True,hide_index=True)
        st.subheader("Extracted text preview")
        for s in segments:
            with st.expander(f"{s.filename} · {s.location} · {s.method} · {s.status}"):
                st.text(s.text[:12000] if reveal else _mask_text(s.text,findings,s.filename,s.location))
    st.subheader("Sanitized output preview")
    preview=gateway.sanitized_text if gateway.allowed else "Gateway blocked: no text is eligible for release."
    st.text_area("Exact simulated downstream payload",preview,height=240,disabled=True)
    st.download_button("Download sanitized text",preview,file_name="sanitized_output.txt",disabled=not gateway.allowed)
    col_a,col_b=st.columns(2)
    col_a.download_button("Download audit JSON",audit_json(findings,reveal),"pii_audit.json","application/json")
    col_b.download_button("Download audit CSV",audit_csv(findings,reveal),"pii_audit.csv","text/csv")
    st.caption("The export sanitizes extracted text only. It does not alter the uploaded source documents.")
else:
    st.info("Add one or more documents to start a local analysis.")
