"""Explainable lexical context detector; avoids downloading a model implicitly."""
from ..models import Segment, Finding

LABELS={"name","contact"}
NON_PERSON_NAME_CONTEXT={"task","workflow","rule","trigger","risk","questionnaire","vendor","third-party"}
PUNCT=" \t\r\n:#-.,;()[]{}"

def detect_contextual(segment: Segment) -> list[Finding]:
    """Find two-token person names only after explicit Name/Contact labels."""
    words=[]; cursor=0
    for raw in segment.text.split():
        start=segment.text.find(raw,cursor); end=start+len(raw); cursor=end
        clean=raw.strip(PUNCT)
        if clean: words.append((clean,start+(len(raw)-len(raw.lstrip(PUNCT))),end-len(raw[len(raw.rstrip(PUNCT)):])) )
    found=[]; i=0
    while i<len(words):
        label=words[i][0].strip(PUNCT).casefold()
        if label not in LABELS:
            i+=1; continue
        previous=words[i-1][0].strip(PUNCT).casefold() if i else ""
        if label=="name" and previous in NON_PERSON_NAME_CONTEXT:
            i+=1; continue
        j=i+1
        while j<len(words) and not words[j][0].strip(PUNCT): j+=1
        # Accept a plain two-part proper name; stop if punctuation or a lower-case word intervenes.
        if j+1<len(words):
            pair=words[j:j+2]
            if all(w and w[0].isupper() and w[1:].islower() for w,_,_ in pair):
                found.append(Finding("PERSON"," ".join(w for w,_,_ in pair),.82,"context-label",segment.filename,segment.location,pair[0][1],pair[1][2],True))
                i=j+2; continue
        i+=1
    return found
