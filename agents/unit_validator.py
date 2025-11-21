"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: unit_validator.py
Description:
    LangGraph node that validates a chosen Field against the Master mapping
    (existence check) and optionally performs an LLM sanity check. Does not
    depend on classifier-populated request.meta.
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import COLLEGE_FIELD_MAPPINGS_DIR, MASTER_COLLEGE_FIELD_MAPPING_JSON
from helpers.field_helpers import _load_units

# from helpers.field_helpers import FieldHelpers
from langgraph.models import (
    UnitValidatorInput,
    UnitValidatorOutput,
    Satisfaction,
    ValidationReport,
)


class UnitValidatorLLM(Protocol):
    """Protocol the injected LLM client must satisfy."""

    def generate_json(self, prompt: str) -> dict | None:
        """Return a raw dict parsed from model output or None on failure."""
        ...


class LLMValidationResponse(BaseModel):
    """Schema for the LLM's validation judgment."""

    is_valid: bool
    reason: str = ""
    removals: List[str] = PydField(
        default_factory=list,
        description="If invalid, suggest field names that should be removed from the provided pool.",
    )


class UnitValidatorNode:
    """
    Node that first verifies structural validity (field presence in the
    master mapping for the given scope). Optionally asks an LLM to confirm
    semantic fit and suggest alternatives. Does not require any meta on the request.
    """

    def __init__(self, llm: Optional[UnitValidatorLLM] = None):
        """
        Parameters
        ----------
        llm : UnitValidatorLLM | None
            An injected LLM with a `generate_json(prompt)` method that returns a raw dict.
        """
        self.llm = llm
        with open(MASTER_COLLEGE_FIELD_MAPPING_JSON, "r", encoding="utf-8") as f:
            # Dict[college, Dict[subject, Dict[field, desc]]]
            self.master: Dict[str, Dict[str, Dict[str, str]]] = json.load(f)

    def Run(self, data: UnitValidatorInput) -> UnitValidatorOutput:
        """
        Execute validation.

        Strategy
        --------
        1) Structural validation: ensure `field_name` exists in the flattened pool,
           optionally filtered by college/subject hints if present on request.meta.
        2) Optional LLM sanity check: pass the request text, chosen field, and the
           valid pool to get (is_valid, reason, suggestions).
        """
        request = data.request
        unit_names = data.unit_names

        college_name = request.college_name

        feedback = data.feedback
        if feedback != None:
            removals = feedback.removals
            additions = feedback.additions
        else:
            removals = None
            additions = None

        # Build the valid pool (same as classifier for consistency).
        valid_pool: Dict[str, str] = _load_units(
            college_name, removals, additions
        )

        exists = all(u in valid_pool for u in unit_names)
        if not exists:
            report = ValidationReport(
                is_valid=False,
                reason="Unit not found in MasterCollegeFieldMapping for the given scope.",
            )
            return UnitValidatorOutput(
                report=report, satisfaction=Satisfaction.Unsatisfied
            )

        if self.llm is not None:
            # Note: still using the word "fields" because it is more intuitive to the llm than "units"
            prompt = (
                "You are validating if the selected Fields match the user's research description.\n"
                "Return strictly JSON with keys: is_valid (bool), reason (string), removals (string array).\n\n"
                f"User text:\n{request.description}\n\n"
                # f"Subject hint: {subject_hint or 'N/A'}\n\n"
                f"Chosen Fields: {unit_names}\n"
                # f"{alt_block}\n\n"
                "If not valid, suggest Fields to remove from this list:\n- "
                + "\n- ".join(list(valid_pool)[:80])
                + "\nOutput ONLY valid JSON. No prose, no markdown.\n"
            )

            raw = self.llm.generate_json(prompt)
            if raw:
                try:
                    parsed = LLMValidationResponse(**raw)
                    report = ValidationReport(
                        is_valid=parsed.is_valid,
                        reason=parsed.reason,
                        # Only return suggestions that actually exist in the pool (safety).
                        removals=[r for r in parsed.removals if r in valid_pool][:3],
                        additions=None,  # can add this later
                    )
                    satisfaction = (
                        Satisfaction.Satisfied
                        if parsed.is_valid
                        else Satisfaction.Unsatisfied
                    )
                    return UnitValidatorOutput(
                        report=report, satisfaction=satisfaction
                    )
                except Exception as e:
                    # If parsing fails, fall back to existence-based validity.
                    print("⚠️ Parse error in UnitValidator LLM response:", e)
            else:
                raise ValueError("Error using unit validator llm. Check credentials.")

        # Fallback: existence ⇒ valid.
        report = ValidationReport(
            is_valid=True, reason="Unit exists in master mapping."
        )
        return UnitValidatorOutput(report=report, satisfaction=Satisfaction.Satisfied)

    # --------------------------
    # helpers
    # --------------------------
    def _Nearest(self, target: str, pool: List[str]) -> List[str]:
        """Return pool entries closest to target using difflib.get_close_matches."""
        return difflib.get_close_matches(target, pool, n=5, cutoff=0.0)


def Build(llm: Optional[UnitValidatorLLM] = None) -> UnitValidatorNode:
    """Factory for LangGraph wiring."""
    return UnitValidatorNode(llm)
