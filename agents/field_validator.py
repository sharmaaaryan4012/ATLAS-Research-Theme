"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_validator.py
Description:
    Validates a chosen Field against <field>.json existence and optionally
    runs an LLM semantic sanity check. No reliance on request.meta.
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import FIELD_SUBFIELD_MAPPINGS_DIR
from helpers.field_helpers import _load_field_mapping
from langgraph.models import (
    Satisfaction,
    FieldValidatorInput,
    FieldValidatorOutput,
    ValidationReport,
)


class FieldValidatorLLM(Protocol):
    def generate_json(self, prompt: str) -> dict | None: ...


class LLMValidationResponse(BaseModel):
    is_valid: bool
    reason: str = ""
    removals: List[str] = PydField(
        default_factory=list,
        description="If invalid, suggest field names that should be removed from the provided pool.",
    )


class FieldValidatorNode:
    def __init__(self, llm: Optional[FieldValidatorLLM] = None):
        self.llm = llm

    def Run(self, data: FieldValidatorInput) -> FieldValidatorOutput:
        request = data.request
        college = request.college_name
        unit_names = data.unit_names
        field_names = data.field_names

        feedback = data.feedback
        if feedback != None:
            removals = feedback.removals
            additions = feedback.additions
        else:
            removals = None
            additions = None

        if not field_names:
            raise ValueError("FieldValidatorNode requires `field_name` context.")

        valid_pool: Dict[str, str] = _load_field_mapping(
            college, unit_names, removals, additions
        )
        exists = all(f in valid_pool for f in field_names)
        if not exists:
            report = ValidationReport(
                is_valid=False,
                reason="Field not found in mapping for the given Field.",
            )
            return FieldValidatorOutput(
                report=report, satisfaction=Satisfaction.Unsatisfied
            )

        if self.llm is not None:
            field_descriptions = {f: valid_pool[f] for f in field_names}

            prompt = (
                "You are validating if the selected Fields match the given research description.\n"
                "Return strictly JSON with keys: is_valid (bool), reason (string), removals (string array).\n\n"
                f"User text:\n{request.description}\n\n"
                f"Chosen Fields: {field_names}\n"
                f"Field descriptions: {field_descriptions}"
                # f"{alt_block}\n\n"
                "If not valid, suggest Fields to remove from the list:\n- "
                + "\n- ".join(list(valid_pool.keys())[:80])
                + "\nRules:\n"
                + "\n - Output ONLY valid JSON. No prose, no markdown.\n"
            )

            raw = self.llm.generate_json(prompt)
            if raw:
                try:
                    parsed = LLMValidationResponse(**raw)
                    report = ValidationReport(
                        is_valid=parsed.is_valid,
                        reason=parsed.reason,
                        removals=[s for s in parsed.removals if s in valid_pool][:3],
                        additions=None,  # can add this later
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
                    print("⚠️ Parse error in FieldValidator LLM response:", e)
            else:
                raise ValueError(
                    "Error using field validator llm. Check credentials."
                )

        # Fallback: existence ⇒ valid.
        report = ValidationReport(
            is_valid=True, reason="Field exists for the given Field."
        )
        return FieldValidatorOutput(
            report=report, satisfaction=Satisfaction.Satisfied
        )

    def _Nearest(self, target: str, pool: List[str]) -> List[str]:
        return difflib.get_close_matches(target, pool, n=5, cutoff=0.0)


def Build(llm: Optional[FieldValidatorLLM] = None) -> FieldValidatorNode:
    return FieldValidatorNode(llm)
