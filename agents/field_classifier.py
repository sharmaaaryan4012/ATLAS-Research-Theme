"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_classifier.py
Description:
    Classifies a user request into one or more fields for a GIVEN unit.
    Reads candidates from FIELD_SUBFIELD_MAPPINGS_DIR/<field>.json and returns
    a ranked list (best-first). No reliance on request.meta.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import FIELD_SUBFIELD_MAPPINGS_DIR
from helpers.field_helpers import _load_field_mapping
from langgraph.models import (
    Candidate,
    FieldClassifierInput,
    FieldClassifierOutput,
)


class FieldClassifierLLM(Protocol):
    def generate_json(self, prompt: str) -> dict | None: ...


class LLMJsonResponse(BaseModel):
    choices: List[Dict[str, str]] = PydField(
        description="List of objects: {'name': <field_name>, 'rationale': <why it matches the research description>}."
    )


class FieldClassifierNode:
    def __init__(self, llm: Optional[FieldClassifierLLM] = None):
        self.llm = llm

    def Run(self, data: FieldClassifierInput) -> FieldClassifierOutput:
        request = data.request
        college = request.college_name
        unit_names = data.unit_names
        if not unit_names:
            raise ValueError("FieldClassifierNode requires `unit_names` context.")

        feedback = data.feedback
        if feedback != None:
            removals = feedback.removals
            additions = feedback.additions
        else:
            removals = None
            additions = None

        candidates: Dict[str, str] = _load_field_mapping(
            college, unit_names, removals, additions
        )
        if not candidates:
            raise ValueError(f"No fields found for units '{unit_names}'.")

        candidate_names = list(candidates.keys())
        research_description = request.description or ""

        prompt = (
            "You are an academic field classifier.\n"
            "Given a research description and a list of candidate fields, "
            "return the fields that best fit the topic.\n"
            "Strictly return a JSON object of the following structure:\n\n"
            "{\n"
            '  "choices": [\n'
            '     {"name": "<field name>", "rationale": "<why it fits>"}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            " - The 'name' MUST be one of the provided candidate fields (verbatim).\n"
            " - Output ONLY valid JSON. No prose, no markdown, no comments.\n\n"
            f"Research description:\n{research_description}\n\n"
            "Candidate fields:\n - " + "\n - ".join(candidate_names[:80])
        )

        parsed_model: Optional[LLMJsonResponse] = None

        raw = self.llm.generate_json(prompt)
        if raw:
            if "choice" in raw and "choices" not in raw:
                raw = {
                    "choices": [
                        {
                            "name": raw.get("choice", ""),
                            "rationale": raw.get("rationale", ""),
                        }
                    ]
                }
            try:
                parsed_model = LLMJsonResponse(**raw)
            except Exception as e:
                print("⚠️ Parse error in FieldClassifier LLM response:", e)
                parsed_model = None
        else:
            raise ValueError("Error using field classifier llm. Check credentials.")

        if parsed_model and parsed_model.choices:
            valid = [c for c in parsed_model.choices if c.get("name") in candidates]
            if valid:
                candidate_objs = [
                    Candidate(
                        name=c["name"], score=1.0, rationale=c.get("rationale", "")
                    )
                    for c in valid
                ]
                return FieldClassifierOutput(
                    candidates=candidate_objs, output_valid=True
                )

        return FieldClassifierOutput(candidates=[], output_valid=False)


def Build(llm: Optional[FieldClassifierLLM] = None) -> FieldClassifierNode:
    return FieldClassifierNode(llm)
