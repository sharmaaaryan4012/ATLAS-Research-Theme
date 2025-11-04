"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_validator.py
Description:
    LangGraph node that validates a chosen Field against the Master mapping
    (existence check) and optionally performs an LLM sanity check. Does not
    depend on classifier-populated request.meta.
"""

from __future__ import annotations

import difflib
import json
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import MASTER_COLLEGE_FIELD_MAPPING_JSON
from helpers.field_helpers import FieldHelpers
from langgraph.models import (
    FieldValidatorInput,
    FieldValidatorOutput,
    Satisfaction,
    ValidationReport,
)


class FieldValidatorLLM(Protocol):
    """Protocol the injected LLM client must satisfy."""

    def generate_json(self, prompt: str) -> dict | None:
        """Return a raw dict parsed from model output or None on failure."""
        ...


class LLMValidationResponse(BaseModel):
    """Schema for the LLM's validation judgment."""

    is_valid: bool
    reason: str = ""
    suggestions: List[str] = PydField(
        default_factory=list,
        description="If invalid, suggest better-suited field names from the provided pool.",
    )


class FieldValidatorNode:
    """
    Node that first verifies structural validity (field presence in the
    master mapping for the given scope). Optionally asks an LLM to confirm
    semantic fit and suggest alternatives. Does not require any meta on the request.
    """

    def __init__(self, llm: Optional[FieldValidatorLLM] = None):
        """
        Parameters
        ----------
        llm : FieldValidatorLLM | None
            An injected LLM with a `generate_json(prompt)` method that returns a raw dict.
        """
        self.llm = llm
        with open(MASTER_COLLEGE_FIELD_MAPPING_JSON, "r", encoding="utf-8") as f:
            # Dict[college, Dict[subject, Dict[field, desc]]]
            self.master: Dict[str, Dict[str, Dict[str, str]]] = json.load(f)

    def Run(self, data: FieldValidatorInput) -> FieldValidatorOutput:
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
        field_name = data.field_name

        # Safely read optional hints if they exist; otherwise None.
        meta = getattr(request, "meta", {}) or {}
        college_name = meta.get("college_name")
        subject_hint = meta.get("subject")

        # Build the valid pool (same as classifier for consistency).
        valid_pool: Dict[str, str] = FieldHelpers.CollectCollegeFields(
            self.master, college_name, subject_hint
        )

        exists = field_name in valid_pool
        if not exists:
            report = ValidationReport(
                is_valid=False,
                reason="Field not found in MasterCollegeFieldMapping for the given scope.",
                suggestions=self._Nearest(field_name, list(valid_pool.keys()))[:3],
            )
            return FieldValidatorOutput(
                report=report, satisfaction=Satisfaction.Unsatisfied
            )

        # Optional LLM sanity check — helpful to catch semantically wrong picks.
        if self.llm is not None:
            desc = valid_pool.get(field_name, "")

            # We no longer rely on classifier-populated candidate_fields;
            # instead show a short list of alternative valid fields (excluding the chosen one).
            alt_names = [n for n in list(valid_pool.keys())[:20] if n != field_name]
            alt_block = ""
            if alt_names:
                alt_block = "\n\nOther valid fields (subset):\n- " + "\n- ".join(alt_names)

            prompt = (
                "You are validating if a selected Field matches the user's subject/request.\n"
                "Return strictly JSON with keys: is_valid (bool), reason (string), suggestions (string array).\n\n"
                f"User text:\n{request.text}\n\n"
                f"Subject hint: {subject_hint or 'N/A'}\n\n"
                f"Chosen Field: {field_name}\n"
                f"Field description: {desc}"
                f"{alt_block}\n\n"
                "If not valid, suggest up to 3 better Fields strictly from this list:\n- "
                + "\n- ".join(list(valid_pool.keys())[:80])
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
                        suggestions=[s for s in parsed.suggestions if s in valid_pool][:3],
                    )
                    satisfaction = (
                        Satisfaction.Satisfied
                        if parsed.is_valid
                        else Satisfaction.Unsatisfied
                    )
                    return FieldValidatorOutput(
                        report=report, satisfaction=satisfaction
                    )
                except Exception as e:
                    # If parsing fails, fall back to existence-based validity.
                    print("⚠️ Parse error in FieldValidator LLM response:", e)

        # Fallback: existence ⇒ valid.
        report = ValidationReport(
            is_valid=True, reason="Field exists in master mapping."
        )
        return FieldValidatorOutput(report=report, satisfaction=Satisfaction.Satisfied)

    # --------------------------
    # helpers
    # --------------------------
    def _Nearest(self, target: str, pool: List[str]) -> List[str]:
        """Return pool entries closest to target using difflib.get_close_matches."""
        return difflib.get_close_matches(target, pool, n=5, cutoff=0.0)


def Build(llm: Optional[FieldValidatorLLM] = None) -> FieldValidatorNode:
    """Factory for LangGraph wiring."""
    return FieldValidatorNode(llm)
