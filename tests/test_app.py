from pathlib import Path
from streamlit.testing.v1 import AppTest
from pii_guard.pipeline import process_uploads
from pii_guard.config import PLACEHOLDERS

ROOT=Path(__file__).resolve().parents[1]

def test_streamlit_upload_review_redaction_and_download_controls():
    fixture=ROOT/"tests"/"fixtures"/"Synthetic_Demo.txt"
    at=AppTest.from_file(str(ROOT/"app.py")).run(timeout=10)
    at.file_uploader[0].upload(fixture.name,fixture.read_bytes(),"text/plain").run(timeout=10)
    assert not at.exception
    assert any("BLOCK" in item.value for item in at.error)
    buttons={item.label:item.proto.disabled for item in at.get("download_button")}
    assert buttons["Download sanitized text"] is True
    assert buttons["Download audit JSON"] is False
    assert buttons["Download audit CSV"] is False

    review_key=next(key for key in at.session_state if key.startswith("review_"))
    at.session_state[review_key]={"edited_rows":{0:{"Reviewer confirmed":True}},"added_rows":[],"deleted_rows":[]}
    at.run(timeout=10)
    assert not at.exception
    assert any("ALLOW" in item.value for item in at.success)
    payload=at.text_area[0].value
    _,findings,_,_,_=process_uploads([(fixture.name,fixture.read_bytes())])
    assert findings
    assert all(f.value not in payload for f in findings)
    assert all(PLACEHOLDERS[f.entity_type] in payload for f in findings)
    buttons={item.label:item.proto.disabled for item in at.get("download_button")}
    assert buttons["Download sanitized text"] is False
