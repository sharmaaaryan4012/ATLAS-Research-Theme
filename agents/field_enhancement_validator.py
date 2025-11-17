"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_enhancement_validator.py
Description:
    LangGraph node that validates user-selected Fields against the master mapping
    (existence check) and optionally performs an LLM sanity check.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import MASTER_COLLEGE_FIELD_MAPPING_JSON
from langgraph.models import (
    FieldEnhancementValidatorInput,
    FieldEnhancementValidatorOutput,
    Satisfaction,
    ValidationReport,
)


class FieldEnhancementValidatorLLM(Protocol):
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
        description=(
            "If invalid, suggest field names that should be removed from "
            "the chosen fields."
        ),
    )


class FieldEnhancementValidatorNode:
    """
    Node that first verifies structural validity (that each chosen field exists
    in the master mapping). Optionally asks an LLM to confirm semantic fit and
    suggest additional removals.

    Structural validation is independent of any classifier-populated metadata;
    it only checks that the field names appear somewhere in the master mapping.
    """

    def __init__(self, llm: Optional[FieldEnhancementValidatorLLM] = None):
        """
        Parameters
        ----------
        llm : FieldEnhancementValidatorLLM | None
            An injected LLM with a `generate_json(prompt)` method that returns a raw dict.
        """
        self.llm = llm
        with open(MASTER_COLLEGE_FIELD_MAPPING_JSON, "r", encoding="utf-8") as f:
            # Dict[college, Dict[subject, Dict[field, desc]]]
            self.master: Dict[str, Dict[str, Dict[str, str]]] = json.load(f)

        # Pre-flatten the set of all known field names for fast existence checks.
        self._all_fields = {
            field_name
            for college_data in self.master.values()
            for subject_data in college_data.values()
            for field_name in subject_data.keys()
        }

    def Run(
        self, data: FieldEnhancementValidatorInput
    ) -> FieldEnhancementValidatorOutput:
        """
        Execute validation.

        Strategy
        --------
        1) Structural validation: ensure each field in `new_field_names` exists
           somewhere in the master mapping.
        2) Optional LLM sanity check: pass the request text and chosen fields
           to get (is_valid, reason, additional removals).
        """
        request = data.request
        field_names: List[str] = data.new_field_names or []

        # 1) Structural validation against master mapping.
        structurally_invalid = [
            name for name in field_names if name not in self._all_fields
        ]

        if structurally_invalid:
            report = ValidationReport(
                is_valid=False,
                reason=(
                    "Some fields are not present in the master mapping: "
                    + ", ".join(structurally_invalid)
                ),
                removals=structurally_invalid,
                additions=None,
            )
            return FieldEnhancementValidatorOutput(
                report=report, satisfaction=Satisfaction.Unsatisfied
            )

        # At this point, all fields exist in the master mapping structurally.

        if self.llm is not None:
            prompt = (
                "You are validating if the selected Fields match the user's research description.\n"
                "Return strictly JSON with keys: is_valid (bool), reason (string), "
                "removals (string array).\n\n"
                f"User text:\n{request.description}\n\n"
                f"Chosen Fields: {field_names}\n\n"
                "If some fields are not good semantic matches, list them in 'removals'. "
                "If all fields are fine, 'removals' should be an empty list.\n"
                "Output ONLY valid JSON. No prose, no markdown.\n"
            )

            raw = self.llm.generate_json(prompt)
            if raw:
                try:
                    parsed = LLMValidationResponse(**raw)
                    # Merge structural and LLM-based removals (structural is already empty here).
                    removals = list(parsed.removals)
                    report = ValidationReport(
                        is_valid=parsed.is_valid,
                        reason=parsed.reason,
                        removals=removals,
                        additions=None,  # can add this later if needed
                    )
                    satisfaction = (
                        Satisfaction.Satisfied
                        if parsed.is_valid
                        else Satisfaction.Unsatisfied
                    )
                    return FieldEnhancementValidatorOutput(
                        report=report, satisfaction=satisfaction
                    )
                except Exception as e:
                    # If parsing fails, fall back to existence-based validity.
                    print(
                        "⚠️ Parse error in FieldEnhancementValidator LLM response:", e
                    )
            else:
                raise ValueError(
                    "Error using field enhancement validator LLM. Check credentials."
                )

        # Fallback: structurally valid ⇒ accepted.
        report = ValidationReport(
            is_valid=True,
            reason="All fields exist in the master mapping and no LLM validation was applied.",
            removals=[],
            additions=None,
        )
        return FieldEnhancementValidatorOutput(
            report=report, satisfaction=Satisfaction.Satisfied
        )


def Build(
    llm: Optional[FieldEnhancementValidatorLLM] = None,
) -> FieldEnhancementValidatorNode:
    """Factory for LangGraph wiring."""
    return FieldEnhancementValidatorNode(llm)
