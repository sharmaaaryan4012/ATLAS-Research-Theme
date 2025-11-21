"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: unit_classifier.py
Description:
    LangGraph node that classifies a user request into one or more academic
    fields using an injected LLM. Produces a list in `candidates`.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from helpers.field_helpers import _load_units
from langgraph.models import (
    Candidate,
    UnitClassifierInput,
    UnitClassifierOutput,
)


# -----------------------------------------------------------------------------
# LLM protocol (interface) — return a plain dict; node will validate/normalize
# -----------------------------------------------------------------------------
class UnitClassifierLLM(Protocol):
    """Protocol the injected LLM client must satisfy."""

    def generate_json(self, prompt: str) -> dict | None:
        """Return a raw dict parsed from model output or None on failure."""
        ...


# -----------------------------------------------------------------------------
# Schema for LLM JSON output (multi-field format)
# -----------------------------------------------------------------------------
class LLMJsonResponse(BaseModel):
    """Schema for LLM output with multiple fields."""

    choices: List[Dict[str, str]] = PydField(
        description=(
            "A list of objects: "
            "{'name': <field_name>, 'rationale': <why it matches the research description>}."
        )
    )


def get_schema() -> str:
    """
    Return the JSON schema (as a pretty-printed string) that the LLM
    should follow in its response.
    """
    generator_response_schema = LLMJsonResponse.model_json_schema()
    generator_response_schema_json = json.dumps(generator_response_schema, indent=2)
    return generator_response_schema_json


class UnitClassifierNode:
    """
    Node that calls an injected LLM to select fields that best match the request.

    The candidate set is derived from the field mapping via `_load_unit_mapping`,
    filtered by `college_name` if present on
    the request.
    """

    def __init__(self, llm: Optional[UnitClassifierLLM]):
        """
        Parameters
        ----------
        llm : UnitClassifierLLM | None
            An injected LLM with a `generate_json(prompt)` method that returns a raw dict.
        """
        self.llm = llm

    def Run(self, data: UnitClassifierInput) -> UnitClassifierOutput:
        """
        Execute classification.

        Parameters
        ----------
        data : UnitClassifierInput
            The user request containing:
              - description
              - college_name (optional)
              - optional feedback (removals/additions for the candidate pool)

        Returns
        -------
        UnitClassifierOutput
            `candidates` holds zero or more selected fields.
            `output_valid` is True if the LLM response could be parsed and
            at least one valid field was selected, False otherwise.
        """
        if self.llm is None:
            raise ValueError("UnitClassifierNode requires an LLM instance.")

        request = data.request
        college_name = request.college_name

        feedback = getattr(data, "feedback", None)
        if feedback is not None:
            removals = feedback.removals
            additions = feedback.additions
        else:
            removals = None
            additions = None

        # Build candidate pool (flattened to {field: description}).
        candidates: Dict[str, str] = _load_units(
            college_name, removals, additions
        )
        if not candidates:
            raise ValueError(
                "No units available from master mapping for college \'" + college_name + "\'. Check data/context."
            )

        research_description = request.description
        # Note: still using the word "fields" because it is more intuitive to the llm than "units"
        prompt = (
            "You are an academic classifier.\n"
            "Given a research description and a list of candidate Fields, "
            "return all the fields that best fit the given research description.\n"
            "Strictly return a JSON object of the following structure:\n\n"
            f"{get_schema()}\n"
            "Rules:\n"
            " - The 'name' MUST be one of the provided candidate fields (verbatim).\n"
            " - Output ONLY valid JSON. No prose, no markdown, no comments.\n\n"
            f"Research description:\n{research_description}\n\n"
            "Candidate Fields and their descriptions:\n"
            f"{candidates}\n"
        )

        parsed_model: Optional[LLMJsonResponse] = None

        raw = self.llm.generate_json(prompt)
        if raw:
            # Backwards-compat: if a single 'choice' is returned, wrap it.
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
            raise ValueError("Error using field classifier LLM. Check credentials.")

        # If the model gave us a structured list, filter to valid fields and return them.
        if parsed_model and parsed_model.choices:
            valid = [c for c in parsed_model.choices if c.get("name") in candidates]
            if valid:
                candidate_objs = [
                    Candidate(
                        name=c["name"],
                        score=1.0,
                        rationale=c.get("rationale", ""),
                    )
                    for c in valid
                ]
                return UnitClassifierOutput(
                    candidates=candidate_objs, output_valid=True
                )

        # If parsing failed or no valid fields, return an invalid output.
        return UnitClassifierOutput(candidates=[], output_valid=False)


def Build(llm: Optional[UnitClassifierLLM] = None) -> UnitClassifierNode:
    """Factory for LangGraph wiring."""
    return UnitClassifierNode(llm)
