from ..models import Finding
from ..config import PLACEHOLDERS

def redact_text(text: str, findings: list[Finding], review_decisions: dict[tuple[str,int,int],bool] | None=None) -> str:
    # Conservatively redact every accepted finding, including pending review.
    # Review controls release through the gateway; they must never leave a raw span in prepared output.
    chosen=[f for f in findings if f.accepted and 0<=f.start<f.end<=len(text)]
    for f in sorted(chosen,key=lambda x:x.start,reverse=True):
        text=text[:f.start]+PLACEHOLDERS.get(f.entity_type,"[REDACTED]")+text[f.end:]
    return text
