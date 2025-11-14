"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_classifier.py
Description:
    LangGraph node that classifies a user request into one or more academic
    fields using an injected LLM. Produces a list in `candidates`.
"""

from __future__ import annotations

import os
import json
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import MASTER_COLLEGE_FIELD_MAPPING_JSON
from helpers.field_helpers import _load_field_mapping
# from helpers.field_helpers import FieldHelpers
from langgraph.models import Candidate, FieldClassifierInput, FieldClassifierOutput, ValidationReport


# -----------------------------------------------------------------------------
# LLM protocol (interface) — return a plain dict; node will validate/normalize
# -----------------------------------------------------------------------------
class FieldClassifierLLM(Protocol):
    """Protocol the injected LLM client must satisfy."""

    def generate_json(self, prompt: str) -> dict | None:
        """Return a raw dict parsed from model output or None on failure."""
        ...


# -----------------------------------------------------------------------------
# Schema for LLM JSON output (multi-field format)
# -----------------------------------------------------------------------------
class LLMJsonResponse(BaseModel):
    """Schema for LLM output with multiple ranked fields."""

    choices: List[Dict[str,str]] = PydField(
        description="A list of objects: {'name': <field_name>, 'rationale': <why it matches the research description>}."
    )

def get_schema():
    generator_response_schema = LLMJsonResponse.model_json_schema()
    generator_response_schema_json = json.dumps(generator_response_schema, indent=2)
    return generator_response_schema_json
            

def LoadMasterMapping() -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Load the master college → subject → {field → description} mapping.

    Returns
    -------
    Dict[str, Dict[str, Dict[str, str]]]
        Nested mapping [college][subject][field] = description.
    """
    with open(MASTER_COLLEGE_FIELD_MAPPING_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


class FieldClassifierNode:
    """
    Node that calls an injected LLM to select up to 3 fields (ranked) that best
    match the request. The candidate set is derived from the master mapping,
    optionally filtered by `college_name` and `subject` if present on request.meta.
    """

    def __init__(self, llm: Optional[FieldClassifierLLM]):
        """
        Parameters
        ----------
        llm : FieldClassifierLLM | None
            An injected LLM with a `generate_json(prompt)` method that returns a raw dict.
        """
        self.llm = llm
        self.master = LoadMasterMapping()

    def Run(self, data: FieldClassifierInput) -> FieldClassifierOutput:
        """
        Execute classification.

        Parameters
        ----------
        data : FieldClassifierInput
            The user request containing text. 
                - 
                - 'college_name'
                - 'subject'

        Returns
        -------
        FieldClassifierOutput
            Ranked `candidates` and `chosen` == top candidate for compatibility.
        """
        request = data.request
        college_name = request.college_name
        department_name = request.department_name

        feedback = data.feedback
        if feedback != None:
            removals = feedback.removals
            additions = feedback.additions
        else:
            removals = None
            additions = None

        # Build candidate pool (flattened to {field: description}).
        candidates: Dict[str, str] = _load_field_mapping(
         college_name, department_name, removals, additions
        )
        if not candidates:
            raise ValueError(
                "No fields available from master mapping. Check data/context."
            )

        candidate_names = list(candidates.keys())

        research_description = request.description
        prompt = (
            "You are an academic classifier.\n"
            "Given a research description and a list of candidate Fields, return all the fields that best fit the given research description.\n"
            "Strictly return a JSON object of the following structure:\n\n"
            f"{get_schema()}" 
            "Rules:\n"
            " - The 'name' MUST be one of the provided candidate fields (verbatim).\n"
            " - Output ONLY valid JSON. No prose, no markdown, no comments.\n\n"
            f"Research description:\n{research_description}\n\n"
            "Candidate Fields and their descriptions:\n- "
            f"{candidates}"
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
                # If the model didn’t match schema, fall back deterministically to first candidate.
                print("⚠️ Parse error in FieldClassifier LLM response:", e)
                parsed_model = None
        else:
            raise ValueError("Error using field classifier llm. Check credentials.")

        # If the model gave us a structured list, filter to valid fields and return them.
        if parsed_model and parsed_model.choices:
            valid = [c for c in parsed_model.choices if c.get("name") in candidates]
            if valid:
                candidate_objs = [
                    Candidate(
                        name=c["name"], score=1.0, rationale=c.get("rationale", "")
                    )
                    for c in valid
                ]
                return FieldClassifierOutput(candidates=candidate_objs)

        # Fallback if no LLM or invalid output: choose first entry deterministically.
        fallback = Candidate(
            name=candidate_names[0],
            score=1.0,
            rationale="Fallback to first candidate; no LLM response or invalid JSON.",
        )
        return FieldClassifierOutput(candidates=[fallback])


def Build(llm: Optional[FieldClassifierLLM] = None) -> FieldClassifierNode:
    """Factory for LangGraph wiring."""
    return FieldClassifierNode(llm)