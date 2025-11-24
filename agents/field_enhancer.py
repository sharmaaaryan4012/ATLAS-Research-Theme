"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_enhancer.py
Description:
    LangGraph node that proposes additional academic fields (beyond an existing
    candidate set) using an injected LLM. New fields are returned in
    `proposed_candidates`.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from helpers.field_helpers import _load_subfield_mapping
from langgraph.models import (
    FieldEnhancerInput,
    FieldEnhancerOutput,
    Candidate,
)


# -----------------------------------------------------------------------------
# LLM protocol (interface) — return a plain dict; node will validate/normalize
# -----------------------------------------------------------------------------
class FieldEnhancerLLM(Protocol):
    """Protocol the injected LLM client must satisfy."""

    def generate_json(self, prompt: str) -> dict | None:
        """Return a raw dict parsed from model output or None on failure."""
        ...


# -----------------------------------------------------------------------------
# Schema for LLM JSON output (multi-field format)
# -----------------------------------------------------------------------------
class LLMJsonResponse(BaseModel):
    """
    Schema for LLM output with optionally multiple proposed fields.

    If the existing Fields already sufficiently classify the description, the
    model should return `choices = null` (i.e., JSON `null`).
    """

    choices: Optional[List[Dict[str, str]]] = PydField(
        description=(
            "A list of objects: "
            "{'name': <field_name>, 'rationale': <why it matches the research description>} "
            "or null if the given Fields sufficiently classify the description."
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


class FieldEnhancerNode:
    """
    Node that calls an injected LLM to propose additional fields that might better
    capture the user's research description.

    The candidate set is derived from the field mapping via `_load_field_mapping`,
    optionally filtered by `college_name` and `department_name`. The enhancer
    asks the LLM for fields that are *not* in this candidate set.
    """

    def __init__(self, llm: Optional[FieldEnhancerLLM]):
        """
        Parameters
        ----------
        llm : FieldEnhancerLLM | None
            An injected LLM with a `generate_json(prompt)` method that returns a raw dict.
        """
        self.llm = llm

    def Run(self, data: FieldEnhancerInput) -> FieldEnhancerOutput:
        """
        Execute enhancement.

        Parameters
        ----------
        data : FieldEnhancerInput
            The user request containing:
              - description
              - college_name 
              - unit_names
              - optional feedback (removals/additions for the candidate pool)

        Returns
        -------
        FieldEnhancerOutput
            `proposed_candidates` is either:
              - a list of Proposal(name, rationale) for newly suggested fields, or
              - None, if no additional fields are needed or parsing failed.
        """
        if self.llm is None:
            raise ValueError("FieldEnhancerNode requires an LLM instance.")

        request = data.request
        candidates = data.subfield_names

        research_description = request.description
        prompt = (
            "You are an academic classifier.\n"
            "Given a research description and a list of candidate Fields, "
            "generate and return any additional Fields that are NOT in the "
            "candidate set but that help better classify the description.\n"
            "If the existing candidate Fields already sufficiently classify the "
            "description, return `choices: null`.\n\n"
            "Strictly return a JSON object of the following structure:\n\n"
            f"{get_schema()}\n"
            "Rules:\n"
            " - Each proposed 'name' MUST NOT be one of the provided candidate fields.\n"
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
                print("⚠️ Parse error in FieldEnhancer LLM response:", e)
                parsed_model = None
        else:
            raise ValueError("Error using field enhancer LLM. Check credentials.")

        # If the model gave us a structured list, keep only genuinely new fields.
        if parsed_model:
            if parsed_model.choices:
                # Filter to names not already in the candidate mapping.
                valid_new = [
                    c
                    for c in parsed_model.choices
                    if c.get("name") and c["name"] not in candidates
                ]
                if valid_new:
                    proposals = [
                        Candidate(
                            name=c["name"],
                            score=1.0,
                            rationale=c.get("rationale", ""),
                        )
                        for c in valid_new
                    ]
                    return FieldEnhancerOutput(proposed_candidates=proposals)
                # If everything was in `candidates` (LLM ignored the rule), treat as no proposals.
                return FieldEnhancerOutput(proposed_candidates=None)
            else:
                # choices is None ⇒ no additional fields needed.
                return FieldEnhancerOutput(proposed_candidates=None)

        # Fallback if parsing failed.
        return FieldEnhancerOutput(proposed_candidates=None)


def Build(llm: Optional[FieldEnhancerLLM] = None) -> FieldEnhancerNode:
    """Factory for LangGraph wiring."""
    return FieldEnhancerNode(llm)
