from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List




@dataclass
class FieldDecision:
    """Decision object for a Field classification step.


    TODO:
    - Add score_breakdown for better tracing.
    """

    field_names: Optional[List[str]] = None
    confidence: float = 0.0
    fields_to_remove: Optional[List[str]] = None
    validator_passed: Optional[bool] = None
    need_new_field: Optional[bool] = None
    notes: str = ""




@dataclass
class SubfieldDecision:
    """Decision object for a Subfield classification step.


    TODO:
    - Add parent_field sanity check logic.
    - Support multiple candidate subfields (n-best list).
    """


    subfield_names: Optional[List[str]] = None
    parent_fields: Optional[str] = None
    subfields_to_remove: Optional[List[str]] = None
    confidence: float = 0.0
    validator_passed: Optional[bool] = None
    need_new_subfield: Optional[bool] = None
    notes: str = ""

@dataclass
class ClassificationBundle:
    """Full result across Field + Subfield passes.


    TODO:
    - Add timestamps for each stage.
    - Add provenance for tool/agent versions.
    - Add error surfaces / exceptions encountered.
    """


    request_text: str = None
    fields: FieldDecision = field(default_factory=FieldDecision)
    subfields: SubfieldDecision = field(default_factory=SubfieldDecision)
    satisfied_fields: Optional[bool] = None
    satisfied_subfields: Optional[bool] = None
    finalized_label: Optional[str] = None # e.g., "Field::Subfield"
    meta: Dict[str, Any] = field(default_factory=dict)