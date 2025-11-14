"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: subfield_validator.py
Description:
    Validates a chosen Subfield against <field>.json existence and optionally
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
from helpers.field_helpers import _load_subfield_mapping
from langgraph.models import (
    Satisfaction,
    SubfieldValidatorInput,
    SubfieldValidatorOutput,
    ValidationReport,
)


class SubfieldValidatorLLM(Protocol):
    def generate_json(self, prompt: str) -> dict | None: ...


class LLMValidationResponse(BaseModel):
    is_valid: bool
    reason: str = ""
    removals: List[str] = PydField(
        default_factory=list,
        description="If invalid, suggest subfield names that should be removed from the provided pool.",
    )


class SubfieldValidatorNode:
    def __init__(self, llm: Optional[SubfieldValidatorLLM] = None):
        self.llm = llm

    def Run(self, data: SubfieldValidatorInput) -> SubfieldValidatorOutput:
        request = data.request
        subfield_names = data.subfield_names
        field_names = data.field_names

        feedback = data.feedback
        if feedback != None:
            removals = feedback.removals
            additions = feedback.additions
        else:
            removals = None
            additions = None

        if not field_names:
            raise ValueError("SubfieldValidatorNode requires `field_name` context.")

        valid_pool: Dict[str, str] = _load_subfield_mapping(
            field_names, additions, removals
        )
        exists = all(s in valid_pool for s in subfield_names)
        if not exists:
            report = ValidationReport(
                is_valid=False,
                reason="Subfield not found in mapping for the given Field.",
            )
            return SubfieldValidatorOutput(
                report=report, satisfaction=Satisfaction.Unsatisfied
            )

        if self.llm is not None:
            subfield_descriptions = {d: valid_pool[d] for d in subfield_names}

            # # Provide a small alternative set (subset of pool excluding chosen)
            # alt_names = [n for n in list(valid_pool.keys())[:20] if n != subfield_names]
            # alt_block = ""
            # if alt_names:
            #     alt_block = "\n\nOther valid subfields (subset):\n- " + "\n- ".join(alt_names)

            prompt = (
                "You are validating if the selected Subfields match the given research description.\n"
                "Return strictly JSON with keys: is_valid (bool), reason (string), removals (string array).\n\n"
                f"User text:\n{request.description}\n\n"
                f"Chosen Subfields: {subfield_names}\n"
                f"Subfield descriptions: {subfield_descriptions}"
                # f"{alt_block}\n\n"
                "If not valid, suggest subfields to remove from the list:\n- "
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
                    return SubfieldValidatorOutput(
                        report=report, satisfaction=satisfaction
                    )
                except Exception as e:
                    print("⚠️ Parse error in SubfieldValidator LLM response:", e)
            else:
                raise ValueError(
                    "Error using subfield validator llm. Check credentials."
                )

        # Fallback: existence ⇒ valid.
        report = ValidationReport(
            is_valid=True, reason="Subfield exists for the given Field."
        )
        return SubfieldValidatorOutput(
            report=report, satisfaction=Satisfaction.Satisfied
        )

    def _Nearest(self, target: str, pool: List[str]) -> List[str]:
        return difflib.get_close_matches(target, pool, n=5, cutoff=0.0)


def Build(llm: Optional[SubfieldValidatorLLM] = None) -> SubfieldValidatorNode:
    return SubfieldValidatorNode(llm)
