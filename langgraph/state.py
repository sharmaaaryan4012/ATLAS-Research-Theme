"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: state.py
Description:
    Shared mutable state for LangGraph execution. Tracks the request, the
    evolving classification decisions, validator reports, and a simple
    event log for auditability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import (
    Candidate,
    Satisfaction,
    UserRequest,
    ValidationReport,
)


@dataclass
class State:
    request: UserRequest
    field_candidates: List[Candidate] = field(default_factory=list)
    chosen_field: Optional[Candidate] = None
    field_validation: Optional[ValidationReport] = None
    field_satisfaction: Optional[Satisfaction] = None

    subfield_candidates: List[Candidate] = field(default_factory=list)
    chosen_subfield: Optional[Candidate] = None
    subfield_validation: Optional[ValidationReport] = None
    subfield_satisfaction: Optional[Satisfaction] = None

    log: List[Dict[str, Any]] = field(default_factory=list)

    def record(self, event: str, **payload: Any) -> None:
        self.log.append({"event": event, **payload})
