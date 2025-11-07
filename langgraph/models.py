"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: models.py
Description:
    Typed dataclasses for messages exchanged between LangGraph nodes. These
    define stable interfaces and aid testability and traceability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeName(str, Enum):
    """Canonical node names for audit trails and updates."""

    Request = "request"
    FieldClassifier = "field_classifier"
    FieldValidator = "field_validator"
    FieldEnhancer = "field_enhancer"
    FieldUpdater = "field_updater"
    SubfieldClassifier = "subfield_classifier"
    SubfieldValidator = "subfield_validator"
    SubfieldEnhancer = "subfield_enhancer"
    SubfieldUpdater = "subfield_updater"


class Decision(str, Enum):
    """Binary decisions returned by validators/guards."""

    Accept = "accept"
    Reject = "reject"


class Satisfaction(str, Enum):
    """Satisfaction state after validation or sanity checks."""

    Satisfied = "satisfied"
    Unsatisfied = "unsatisfied"


def now_iso() -> str:
    """UTC timestamp in ISO 8601 for auditability."""
    return datetime.now(timezone.utc).isoformat()


# --------------------------
# Core request/response types
# --------------------------
@dataclass
class UserRequest:
    """
    The original user input and any optional context.

    Attributes
    ----------
    request_id : str
        Unique identifier for the request (for tracing in logs/DB).
    text : str
        Free-form description or query text.
    college_name : str
        Name of college for identification in mappings
    department_name : str
        Name of department for identification in mappings.
    meta : Dict[str, Any]
        Optional context, e.g., {'college_name': ..., 'subject': ..., 'candidate_fields': [...] }.
    """

    request_id: str
    text: str
    college_name: str
    department_name: str


@dataclass
class Candidate:
    """
    A single ranked candidate label.

    Attributes
    ----------
    name : str
        The field/subfield name.
    score : float
        Model-specific score; relative only (1.0 used as opaque default).
    rationale : str
        Short reason why this candidate fits.
    """

    name: str
    score: float
    rationale: str = ""


@dataclass
class ValidationReport:
    """
    Structured report from a validator.

    Attributes
    ----------
    is_valid : bool
        Whether the proposed label passes the check.
    reason : str
        Human-readable justification for the decision.
    removals : List[str]
        If invalid, list of items to remove.
    """

    is_valid: bool
    reason: str = ""
    removals: List[str] = field(default_factory=list)


@dataclass
class Proposal:
    """
    Proposal for adding a new field/subfield to the canonical mapping.
    """

    proposed_name: str
    rationale: str = ""
    evidence: List[str] = field(default_factory=list)


@dataclass
class MappingUpdate:
    """
    Represents an update into the canonical mapping.

    Attributes
    ----------
    level : str
        Either "field" or "subfield".
    parent_field : Optional[str]
        Required when adding a subfield.
    name : str
        New entry name to insert into the mapping.
    created_by : NodeName
        Node that produced the update.
    created_at : str
        ISO timestamp for auditability.
    """

    level: str  # "field" or "subfield"
    parent_field: Optional[str] = None
    name: str = ""
    created_by: NodeName = NodeName.FieldUpdater
    created_at: str = field(default_factory=now_iso)


# --------------------------
# Field pipeline
# --------------------------
@dataclass
class FieldClassifierInput:
    """Input to the field classifier node."""

    request: UserRequest


@dataclass
class FieldClassifierOutput:
    """
    Output from the field classifier.

    Attributes
    ----------
    candidates : List[Candidate]
        Ranked list of field candidates (best-first).
    """

    candidates: List[Candidate] = field(default_factory=list)


@dataclass
class FieldValidatorInput:
    """Input to the field validator node."""

    field_name: str
    request: UserRequest


@dataclass
class FieldValidatorOutput:
    """Output from the field validator node."""

    report: ValidationReport
    satisfaction: Satisfaction


# --------------------------
# Field enhancement/updater (stubs available for expansion)
# --------------------------
@dataclass
class FieldEnhancerInput:
    """Input to a (future) field enhancer node."""

    request: UserRequest
    attempted_field: str


@dataclass
class FieldEnhancerOutput:
    """Output from a (future) field enhancer node."""

    proposal: Proposal


@dataclass
class FieldUpdaterInput:
    """Input to the mapping updater node."""

    proposal: Proposal


@dataclass
class FieldUpdaterOutput:
    """Output from the mapping updater node."""

    update: MappingUpdate


# --------------------------
# Subfield pipeline (placeholders for parity)
# --------------------------
@dataclass
class SubfieldClassifierInput:
    """Input to the subfield classifier node."""

    request: UserRequest
    field_name: str


@dataclass
class SubfieldClassifierOutput:
    """Output from the subfield classifier node."""

    candidates: List[Candidate] = field(default_factory=list)


@dataclass
class SubfieldValidatorInput:
    """Input to the subfield validator node."""

    subfield_name: str
    field_name: str
    request: UserRequest


@dataclass
class SubfieldValidatorOutput:
    """Output from the subfield validator node."""

    report: ValidationReport
    satisfaction: Satisfaction


@dataclass
class SubfieldEnhancerInput:
    """Input to the subfield enhancer node."""

    request: UserRequest
    field_name: str
    attempted_subfield: str


@dataclass
class SubfieldEnhancerOutput:
    """Output from the subfield enhancer node."""

    proposal: Proposal


@dataclass
class SubfieldUpdaterInput:
    """Input to the subfield updater node."""

    proposal: Proposal
    field_name: str


@dataclass
class SubfieldUpdaterOutput:
    """Output from the subfield updater node."""

    update: MappingUpdate
