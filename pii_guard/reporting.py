import csv, io, json
from dataclasses import asdict
from .models import Finding

def _records(findings: list[Finding], reveal: bool):
    records=[asdict(f) for f in findings]
    if not reveal:
        for record in records: record["value"]="[HIDDEN]"
    return records

def audit_json(findings: list[Finding], reveal: bool=False) -> str:
    return json.dumps(_records(findings,reveal),indent=2)

def audit_csv(findings: list[Finding], reveal: bool=False) -> str:
    buf=io.StringIO(); fields=list(asdict(findings[0]).keys()) if findings else ["entity_type","value","confidence","method","filename","location","start","end","review_required","accepted"]
    w=csv.DictWriter(buf,fieldnames=fields); w.writeheader(); w.writerows(_records(findings,reveal)); return buf.getvalue()
