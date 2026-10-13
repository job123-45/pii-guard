from dataclasses import asdict, dataclass
from typing import Any

@dataclass
class Segment:
    filename: str
    location: str
    method: str
    text: str
    status: str = "ok"
    review_required: bool = False

@dataclass
class Finding:
    entity_type: str
    value: str
    confidence: float
    method: str
    filename: str
    location: str
    start: int
    end: int
    review_required: bool = False
    accepted: bool = True
    reviewed: bool = False
    def public_dict(self, reveal: bool = False) -> dict[str, Any]:
        d=asdict(self)
        if not reveal: d["value"] = "[HIDDEN]"
        return d
