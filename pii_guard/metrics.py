def score_predictions(expected: set[tuple[str,str]], predicted: set[tuple[str,str]]) -> dict[str,float|int]:
    tp=len(expected & predicted); fp=len(predicted-expected); fn=len(expected-predicted)
    precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"tp":tp,"fp":fp,"fn":fn,"precision":precision,"recall":recall,"f1":f1}

def structure_retention(source_segments: int, output_segments: int) -> float:
    return min(output_segments/source_segments,1.0) if source_segments else 0.0
