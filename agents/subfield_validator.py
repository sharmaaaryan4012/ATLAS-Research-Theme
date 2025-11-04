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
from langgraph.models import (
    Satisfaction,
    SubfieldValidatorInput,
    SubfieldValidatorOutput,
    ValidationReport,
)


class SubfieldValidatorLLM(Protocol):
    def generate_json(self, prompt: str) -> dict | None:
        ...


class LLMValidationResponse(BaseModel):
    is_valid: bool
    reason: str = ""
    suggestions: List[str] = PydField(default_factory=list)


def _load_subfield_mapping(field_name: str) -> Dict[str, str]:
    filename = f"{field_name}.json"
    path = os.path.join(FIELD_SUBFIELD_MAPPINGS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class SubfieldValidatorNode:
    def __init__(self, llm: Optional[SubfieldValidatorLLM] = None):
        self.llm = llm

    def Run(self, data: SubfieldValidatorInput) -> SubfieldValidatorOutput:
        request = data.request
        subfield_name = data.subfield_name
        field_name = data.field_name
        if not field_name:
            raise ValueError("SubfieldValidatorNode requires `field_name` context.")

        valid_pool: Dict[str, str] = _load_subfield_mapping(field_name)
        exists = subfield_name in valid_pool
        if not exists:
            report = ValidationReport(
                is_valid=False,
                reason="Subfield not found in mapping for the given Field.",
                suggestions=self._Nearest(subfield_name, list(valid_pool.keys()))[:3],
            )
            return SubfieldValidatorOutput(
                report=report, satisfaction=Satisfaction.Unsatisfied
            )

        if self.llm is not None:
            desc = valid_pool.get(subfield_name, "")

            # Provide a small alternative set (subset of pool excluding chosen)
            alt_names = [n for n in list(valid_pool.keys())[:20] if n != subfield_name]
            alt_block = ""
            if alt_names:
                alt_block = "\n\nOther valid subfields (subset):\n- " + "\n- ".join(alt_names)

            prompt = (
                "You are validating if a selected Subfield matches the user's subject/request.\n"
                "Return strictly JSON with keys: is_valid (bool), reason (string), suggestions (string array).\n\n"
                f"User text:\n{request.text}\n\n"
                f"Top-level Field: {field_name}\n"
                f"Chosen Subfield: {subfield_name}\n"
                f"Subfield description: {desc}"
                f"{alt_block}\n\n"
                "If not valid, suggest up to 3 better Subfields strictly from this list:\n- "
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
                        suggestions=[s for s in parsed.suggestions if s in valid_pool][:3],
                    )
                    satisfaction = (
                        Satisfaction.Satisfied if parsed.is_valid else Satisfaction.Unsatisfied
                    )
                    return SubfieldValidatorOutput(report=report, satisfaction=satisfaction)
                except Exception as e:
                    print("⚠️ Parse error in SubfieldValidator LLM response:", e)

        # Fallback: existence ⇒ valid.
        report = ValidationReport(is_valid=True, reason="Subfield exists for the given Field.")
        return SubfieldValidatorOutput(report=report, satisfaction=Satisfaction.Satisfied)

    def _Nearest(self, target: str, pool: List[str]) -> List[str]:
        return difflib.get_close_matches(target, pool, n=5, cutoff=0.0)


def Build(llm: Optional[SubfieldValidatorLLM] = None) -> SubfieldValidatorNode:
    return SubfieldValidatorNode(llm)
