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
        # Collapse exact duplicates first (a labelled-name rule and spaCy can
        # identify the same span), then prefer higher-confidence spans when
        # distinct detector results overlap.
        unique = {}
        for finding in candidates:
            key = (finding.entity_type, finding.start, finding.end, finding.value)
            current = unique.get(key)
            if current is None or finding.confidence > current.confidence:
                unique[key] = finding

        chosen = []
        for finding in sorted(
            unique.values(),
            key=lambda f: (-f.confidence, f.start, -(f.end - f.start), f.entity_type),
        ):
            if any(finding.start < prior.end and prior.start < finding.end for prior in chosen):
                continue
            chosen.append(finding)
        out.extend(sorted(chosen, key=lambda f: (f.start, f.end)))
    return out
