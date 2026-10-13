import re

from ..models import Finding
from ..config import PLACEHOLDERS

def redact_text(text: str, findings: list[Finding], review_decisions: dict[tuple[str,int,int],bool] | None=None) -> str:
    # Conservatively redact every accepted finding, including pending review.
    # Remove every occurrence of each detected value in this source segment, not
    # only the detected span, so repeats cannot survive in sanitized output.
    chosen=[f for f in findings if f.accepted and 0<=f.start<f.end<=len(text)]
    replacements = {}
    for finding in chosen:
        if finding.value:
            replacements.setdefault(finding.value, PLACEHOLDERS.get(finding.entity_type,"[REDACTED]"))
    if replacements:
        ordered = sorted(replacements, key=len, reverse=True)
        matcher = re.compile("|".join(re.escape(value) for value in ordered), re.IGNORECASE)
        folded_placeholders = {value.casefold(): placeholder for value, placeholder in replacements.items()}
        text = matcher.sub(lambda match: folded_placeholders[match.group(0).casefold()], text)
    return text
