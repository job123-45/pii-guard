from collections import Counter
import hashlib

import pandas as pd
import streamlit as st

from pii_guard.extractors.ocr_engine import ocr_available
from pii_guard.detection.ner_detector import person_ner_status
from pii_guard.gateway import decide_gateway
from pii_guard.pipeline import process_uploads
from pii_guard.redaction.text_redactor import redact_text
from pii_guard.reporting import audit_csv, audit_json


def _mask_text(text, findings, filename, location):
    segment_findings = [
        finding
        for finding in findings
        if finding.filename == filename and finding.location == location
    ]
    decisions = {
        (finding.filename, finding.start, finding.end): True
        for finding in segment_findings
    }
    return redact_text(text, segment_findings, decisions)


def _render_styles():
    st.markdown(
        """
        <style>
        :root {
            --ink: #17243a;
            --muted: #718096;
            --orange: #f47b3a;
            --orange-deep: #dd5d25;
            --line: #e6ebf2;
            --paper: #ffffff;
            --canvas: #f3f6fa;
        }
        html, body, [class*="css"] { font-family: 'Aptos', 'Segoe UI', sans-serif; }
        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stHeader"] { background: rgba(243,246,250,.85); }
        .block-container { max-width: 1440px; padding: 2rem 3rem 4rem; }
        h1, h2, h3 { color: var(--ink); font-family: 'Aptos Display', 'Segoe UI', sans-serif; letter-spacing: -.035em; }
        h2 { font-size: 1.35rem !important; }
        [data-testid="stSidebar"] { background: #111d31; border-right: 1px solid #23314a; }
        [data-testid="stSidebar"] * { color: #eaf0f7; }
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label p { color: #d7e0ec; }
        [data-testid="stSidebar"] hr { border-color: #2d3b53; }
        .brand-lockup { display:flex; align-items:center; gap:.75rem; padding:.35rem 0 1.4rem; }
        .brand-icon { width:42px; height:42px; border-radius:14px; display:grid; place-items:center;
            color:white; font-size:20px; background:linear-gradient(145deg,#ff9a55,#eb642e);
            box-shadow:0 8px 24px rgba(244,123,58,.25); }
        .brand-name { font:800 1rem 'Aptos Display','Segoe UI',sans-serif; letter-spacing:.02em; color:#fff; }
        .brand-note { display:block; color:#9eacc0; font-size:.68rem; letter-spacing:.14em; margin-top:2px; }
        .hero { position:relative; overflow:hidden; display:flex; justify-content:space-between; gap:2rem;
            padding:2.1rem 2.3rem; margin:0 0 1.25rem; border-radius:24px;
            background:radial-gradient(ellipse at 93% 15%,rgba(244,123,58,.24),transparent 34%),
            linear-gradient(120deg,#14223a 0%,#1d2d47 65%,#273652 100%);
            box-shadow:0 20px 55px rgba(26,42,67,.14); }
        .hero:after { content:''; position:absolute; width:250px; height:250px; right:15%; bottom:-205px;
            border:1px solid rgba(255,255,255,.12); border-radius:50%; box-shadow:0 0 0 30px rgba(255,255,255,.025),0 0 0 62px rgba(255,255,255,.025); }
        .hero-copy, .hero-status { position:relative; z-index:1; }
        .hero-kicker { color:#ffb17d; font-size:.68rem; font-weight:700; letter-spacing:.19em; text-transform:uppercase; }
        .hero h1 { color:#fff; font:800 clamp(2rem,3.1vw,3.1rem) 'Aptos Display','Segoe UI',sans-serif; letter-spacing:-.04em; line-height:1.06; margin:.8rem 0 .75rem; }
        .hero h1 span { color:#ff9a5d; }
        .hero-subtitle { color:#c1ccda; max-width:650px; line-height:1.65; font-size:.98rem; margin:0; }
        .hero-status { align-self:center; min-width:210px; padding:1.15rem 1.25rem; border-radius:18px;
            border:1px solid rgba(255,255,255,.13); background:rgba(255,255,255,.07); backdrop-filter:blur(8px); }
        .hero-status .status-eyebrow { font-size:.63rem; color:#aebbd0; letter-spacing:.15em; text-transform:uppercase; }
        .hero-status strong { display:block; color:#fff; font:700 1.18rem 'Aptos Display','Segoe UI',sans-serif; margin:.35rem 0; }
        .hero-status small { color:#bdc9d8; line-height:1.5; }
        .section-kicker { color:#8794a8; font-size:.67rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; margin:.4rem 0 .7rem; }
        .upload-intro { border:1px solid var(--line); background:white; border-radius:18px; padding:1.15rem 1.35rem .65rem; margin-bottom:.65rem; }
        .upload-intro strong { color:var(--ink); font:700 1rem 'Aptos Display','Segoe UI',sans-serif; }
        .upload-intro p { color:var(--muted); margin:.3rem 0 .65rem; font-size:.86rem; }
        [data-testid="stFileUploader"] { border:1px dashed #cbd4e1; border-radius:14px; background:#fafbfd; padding:.6rem; }
        [data-testid="stFileUploader"] section { border:0; background:transparent; }
        [data-testid="stFileUploader"] button,
        [data-testid="stFileUploaderDropzone"] button,
        [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
            background:#f47b3a !important; background-color:#f47b3a !important;
            color:#ffffff !important; border:1px solid #f47b3a !important;
            border-radius:10px !important; font-weight:700 !important;
        }
        [data-testid="stFileUploader"] button *,
        [data-testid="stFileUploaderDropzone"] button * { color:#ffffff !important; fill:#ffffff !important; }
        [data-testid="stFileUploader"] button:hover,
        [data-testid="stFileUploaderDropzone"] button:hover {
            background:#dd5d25 !important; background-color:#dd5d25 !important;
            color:#ffffff !important; border-color:#dd5d25 !important;
        }
        [data-testid="stFileUploader"] button:focus-visible,
        [data-testid="stFileUploaderDropzone"] button:focus-visible {
            outline:3px solid rgba(244,123,58,.3) !important; outline-offset:2px;
        }
        .stButton button { border-radius:10px !important; }
        .stButton button[kind="primary"], .stDownloadButton button[kind="primary"] { background:var(--orange); border-color:var(--orange); }
        [data-testid="stMetric"] { background:var(--paper); border:1px solid var(--line); border-radius:16px;
            padding:1rem 1.15rem; box-shadow:0 5px 18px rgba(28,45,70,.035); }
        [data-testid="stMetricLabel"] { color:#748198 !important; font-size:.76rem; font-weight:600; }
        [data-testid="stMetricValue"] { color:var(--ink); font:800 1.8rem 'Aptos Display','Segoe UI',sans-serif; }
        [data-testid="stAlert"] { border-radius:14px; border-width:1px; }
        div[data-testid="stExpander"] { background:#fff; border:1px solid var(--line); border-radius:14px; }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] { border:1px solid var(--line); border-radius:13px; overflow:hidden; }
        .stTextArea textarea { border-radius:14px; border:1px solid var(--line); background:#f9fbfd; }
        .stCaption, [data-testid="stCaptionContainer"] { color:#7b879a; }
        .empty-state { display:flex; align-items:flex-start; gap:1rem; border:1px solid #e4eaf1;
            border-radius:18px; padding:1.3rem 1.45rem; margin-top:.65rem; background:linear-gradient(110deg,#fff,#f9fbfd); }
        .empty-icon { display:grid; place-items:center; width:42px; height:42px; flex:0 0 42px; border-radius:13px;
            background:#fff0e7; color:#df642d; font-size:20px; }
        .empty-state strong { color:var(--ink); font:700 1rem 'Aptos Display','Segoe UI',sans-serif; }
        .empty-state p { margin:.28rem 0 0; color:var(--muted); line-height:1.55; font-size:.88rem; }
        @media(max-width:850px) {
            .block-container { padding:1.2rem 1rem 3rem; }
            .hero { flex-direction:column; padding:1.6rem; }
            .hero-status { align-self:stretch; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Optiv PII Guard | Cadence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
_render_styles()

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-icon">◈</div>'
        '<div><span class="brand-name">OPTIV PII GUARD</span>'
        '<span class="brand-note">PRIVACY OPERATIONS</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Review controls")
    st.caption("Local review settings")
    reveal = st.checkbox(
        "Reveal detected values",
        value=False,
        help="Sensitive source content may appear on screen.",
    )
    if reveal:
        st.error("Sensitive values are visible in this session.")
    simulate_failure = st.checkbox("Simulate validation failure")
    st.divider()
    st.markdown("**Extraction engine**")
    if ocr_available():
        st.success("Tesseract ready", icon="🟢")
        st.caption("Scanned PDF pages can be processed locally.")
    else:
        st.error("Tesseract unavailable", icon="⚠️")
        st.caption("Scanned pages will fail closed until OCR is available.")
    st.divider()
    st.caption("Cadence Financial Group · Internal privacy review")
    st.divider()
    ner_available, ner_message = person_ner_status()
    st.markdown("**Person-name detection**")
    if ner_available:
        st.success("Contextual NER ready", icon="🧠")
    else:
        st.error("Contextual NER unavailable", icon="⚠️")
    st.caption(ner_message)

st.markdown(
    '<section class="hero"><div class="hero-copy">'
    '<div class="hero-kicker">Document privacy operations</div>'
    '<h1>Protect sensitive data<br><span>before it reaches AI.</span></h1>'
    '<p class="hero-subtitle">Review document extractions, resolve PII findings, and release only '
    'sanitized text through a fail-closed gateway.</p></div>'
    '<div class="hero-status"><span class="status-eyebrow">Gateway posture</span>'
    '<strong>Fail closed by design</strong><small>Incomplete extraction or unresolved review keeps the payload blocked.</small>'
    '</div></section>',
    unsafe_allow_html=True,
)
st.markdown('<div class="section-kicker">01 &nbsp; Start a document review</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="upload-intro"><strong>Bring in a document</strong>'
    '<p>PDF, Word, PowerPoint or plain text · Files are processed locally in this prototype.</p></div>',
    unsafe_allow_html=True,
)
uploads = st.file_uploader(
    "Choose files or drag them here",
    type=["pdf", "docx", "pptx", "txt"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.caption("Review the extracted text and each finding before sharing. No original document is sent to an AI provider.")

if uploads:
    data = [(upload.name, upload.getvalue()) for upload in uploads]
    with st.spinner("Extracting, scanning and redacting locally..."):
        segments, findings, redacted, gateway, errors = process_uploads(
            data, validation_ok=not simulate_failure
        )

    st.markdown('<div class="section-kicker">02 &nbsp; Review results</div>', unsafe_allow_html=True)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Documents", len(uploads), help="Files in this review batch")
    metric_columns[1].metric("Extracted segments", len(segments), help="Pages, slides and text blocks")
    metric_columns[2].metric("PII findings", len(findings), help="Candidate findings from enabled detectors")
    metric_columns[3].metric(
        "Needs review",
        sum(finding.review_required and not finding.reviewed for finding in findings),
        help="Findings still awaiting reviewer confirmation",
    )

    if errors:
        with st.expander(f"Extraction notices · {len(errors)}", expanded=True):
            for error in errors:
                st.warning(error)

    pdf_pages = [
        segment
        for segment in segments
        if segment.filename.lower().endswith(".pdf") and segment.location.startswith("page:")
    ]
    if pdf_pages:
        with st.expander("PDF page extraction status", expanded=False):
            status_counts = Counter(segment.status for segment in pdf_pages)
            st.caption(
                f"{status_counts.get('ok', 0)} of {len(pdf_pages)} PDF pages have non-empty extracted text. "
                "Failed or uncertain pages block release."
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Document": segment.filename,
                            "Page": segment.location,
                            "Method": segment.method,
                            "Status": segment.status,
                            "Characters": len(segment.text),
                        }
                        for segment in pdf_pages
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown('<div class="section-kicker">03 &nbsp; Findings and reviewer decisions</div>', unsafe_allow_html=True)
    review_rows = [
        {
            "Finding": index + 1,
            "Category": finding.entity_type,
            "Source": finding.filename + " · " + finding.location,
            "Confidence": finding.confidence,
            "Value": finding.value if reveal else "[HIDDEN]",
            "Needs review": finding.review_required,
            "Reviewer confirmed": finding.reviewed,
        }
        for index, finding in enumerate(findings)
    ]
    if review_rows:
        upload_fingerprint = hashlib.sha256(b"".join(content for _, content in data)).hexdigest()[:16]
        review_key = "review_" + upload_fingerprint
        reviewed_df = st.data_editor(
            pd.DataFrame(review_rows),
            key=review_key,
            use_container_width=True,
            hide_index=True,
            disabled=["Finding", "Category", "Source", "Confidence", "Value", "Needs review"],
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence", min_value=0.0, max_value=1.0, format="%.0%%"
                ),
                "Reviewer confirmed": st.column_config.CheckboxColumn(
                    "Reviewer confirmed",
                    help="Confirm the detection is valid; the span will then be redacted before release.",
                ),
            },
        )
        for index, finding in enumerate(findings):
            finding.reviewed = bool(reviewed_df.iloc[index]["Reviewer confirmed"])

        redacted = []
        for segment in segments:
            segment_findings = [
                finding
                for finding in findings
                if finding.filename == segment.filename and finding.location == segment.location
            ]
            decisions = {
                (finding.filename, finding.start, finding.end): finding.reviewed
                for finding in segment_findings
            }
            redacted.append((segment, redact_text(segment.text, segment_findings, decisions)))
        sanitized = "\n\n".join(
            f"[{segment.filename} | {segment.location}]\n{text}"
            for segment, text in redacted
            if segment.status == "ok"
        )
        gateway = decide_gateway(segments, findings, sanitized, errors, True, not simulate_failure)

    st.markdown('<div class="section-kicker">04 &nbsp; Gateway decision</div>', unsafe_allow_html=True)
    status_message = (
        "AI gateway ALLOW — simulated sanitized handoff only."
        if gateway.allowed
        else "AI gateway BLOCK — " + " ".join(gateway.reasons)
    )
    (st.success if gateway.allowed else st.error)(status_message)

    summary_left, summary_right = st.columns([1.05, 0.95], gap="large")
    with summary_left:
        st.markdown("#### Finding overview")
        categories = Counter(finding.entity_type for finding in findings)
        if categories:
            chart_data = pd.DataFrame(
                [{"Category": category.replace("_", " "), "Findings": count} for category, count in sorted(categories.items())]
            )
            st.bar_chart(chart_data, x="Category", y="Findings", color="#f47b3a", height=230)
        else:
            st.info("No candidates were found by the enabled detectors. This is not proof that the document contains no PII.")
    with summary_right:
        st.markdown("#### Detected categories")
        category_rows = [{"Category": category, "Count": count} for category, count in sorted(categories.items())]
        if category_rows:
            st.dataframe(pd.DataFrame(category_rows), use_container_width=True, hide_index=True)

    st.markdown("#### Extracted text preview")
    st.caption("Sensitive spans stay hidden by default. Expand a segment to inspect its masked text.")
    for segment in segments:
        with st.expander(f"{segment.filename}  ·  {segment.location}  ·  {segment.method}  ·  {segment.status}"):
            st.text(segment.text[:12000] if reveal else _mask_text(segment.text, findings, segment.filename, segment.location))

    st.markdown('<div class="section-kicker">05 &nbsp; Sanitized handoff</div>', unsafe_allow_html=True)
    preview = gateway.sanitized_text if gateway.allowed else "Gateway blocked: no text is eligible for release."
    st.text_area("Exact simulated downstream payload", preview, height=220, disabled=True)
    download_left, download_right = st.columns([1, 1])
    with download_left:
        st.download_button(
            "Download sanitized text",
            preview,
            file_name="sanitized_output.txt",
            disabled=not gateway.allowed,
            use_container_width=True,
            type="primary",
        )
    with download_right:
        audit_left, audit_right = st.columns(2)
        audit_left.download_button(
            "Download audit JSON", audit_json(findings, reveal), "pii_audit.json", "application/json", use_container_width=True
        )
        audit_right.download_button(
            "Download audit CSV", audit_csv(findings, reveal), "pii_audit.csv", "text/csv", use_container_width=True
        )
    st.caption("Exports contain sanitized extracted text only; the uploaded PDF, Word or PowerPoint source is not modified.")
else:
    st.markdown(
        '<div class="empty-state"><div class="empty-icon">✦</div><div>'
        '<strong>Your privacy review starts here</strong>'
        '<p>Upload one or more files above. Optiv PII Guard will extract text, identify candidate sensitive values, '
        'and keep the downstream gateway blocked until extraction and review requirements are met.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-kicker" style="margin-top:1.6rem">Built for careful release</div>', unsafe_allow_html=True)
    assurance_a, assurance_b, assurance_c = st.columns(3)
    assurance_a.markdown("**01 · Extract locally**  \nPDF, DOCX, PPTX and TXT parsing stays in this app process.")
    assurance_b.markdown("**02 · Review findings**  \nSensitive candidate values remain hidden until a reviewer chooses to reveal them.")
    assurance_c.markdown("**03 · Fail closed**  \nIncomplete extraction, validation errors or unresolved findings block the payload.")
