from .patterns import PATTERNS
from .ner_detector import detect_contextual
from ..models import Segment, Finding

def detect_pii(segments: list[Segment]) -> list[Finding]:
    out=[]
    for seg in segments:
        candidates=detect_contextual(seg)
        for entity,(pattern,confidence) in PATTERNS.items():
            for m in pattern.finditer(seg.text):
                if "value" in m.groupdict():
                    value=m.group("value"); start=m.start("value"); end=m.end("value")
                else:
                    value=m.group(0); start=m.start(); end=m.end()
                # Trim contextual labels such as "Name:" from the span.
                if entity in {"PERSON","ADDRESS"} and ":" in value:
                    start += value.index(":")+1
                    while start<end and seg.text[start].isspace(): start+=1
                    value=seg.text[start:end]
                candidates.append(Finding(entity,value,confidence,"regex-context" if entity in {"PERSON","ADDRESS"} else "regex",seg.filename,seg.location,start,end,confidence<.85))
        candidates.sort(key=lambda f:(f.start,-f.confidence,-(f.end-f.start)))
        accepted=[]
        for f in candidates:
            if accepted and f.start < accepted[-1].end:
                if f.confidence>accepted[-1].confidence: accepted[-1]=f
            else: accepted.append(f)
        out.extend(accepted)
    return out
