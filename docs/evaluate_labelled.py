"""Score the explicitly labelled synthetic fixture; supplied-document labels remain separate."""
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pii_guard.models import Segment
from pii_guard.detection.pii_engine import detect_pii

fixture=ROOT/"outputs"/"ground_truth_fixture.csv"
rows=list(csv.DictReader(fixture.open(encoding="utf-8-sig",newline="")))
expected=set(); predicted=set(); detail=[]
for row in rows:
    case_id=row["case_id"]
    gold={(case_id,row["gold_entity_type"],row["gold_value"])} if row["gold_entity_type"] else set()
    found=detect_pii([Segment("fixture.txt",case_id,"fixture",row["source_text"])])
    got={(case_id,f.entity_type,f.value) for f in found}
    expected|=gold; predicted|=got
    tp=gold&got; fp=got-gold; fn=gold-got
    detail.append({"case_id":case_id,"source_text":row["source_text"],"gold_entity_type":row["gold_entity_type"],"gold_value":row["gold_value"],
                   "predicted_entities_json":json.dumps([{"type":f.entity_type,"value":f.value} for f in found],ensure_ascii=False),
                   "case_result":"TP" if tp else ("FP" if fp else ("FN" if fn else "TN"))})
tp=len(expected&predicted); fp=len(predicted-expected); fn=len(expected-predicted)
precision=tp/(tp+fp) if tp+fp else 0.0
recall=tp/(tp+fn) if tp+fn else 0.0
result={"tp":tp,"fp":fp,"fn":fn,"tn":sum(r["case_result"]=="TN" for r in detail),
        "precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0.0,
        "labelled_cases":len(rows),"expected_instances":len(expected),"predicted_instances":len(predicted),
        "dataset":"ground_truth_fixture.csv","scope":"synthetic deterministic fixture only; not sample-document performance"}
out=ROOT/"outputs"
(out/"labelled_fixture_metrics.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
with (out/"labelled_fixture_case_results.csv").open("w",newline="",encoding="utf-8-sig") as stream:
    writer=csv.DictWriter(stream,fieldnames=list(detail[0])); writer.writeheader(); writer.writerows(detail)
print(json.dumps(result,indent=2))
