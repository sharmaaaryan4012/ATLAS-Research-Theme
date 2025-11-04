"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: field_classifier.py
Description:
    LangGraph node that classifies a user request into one or more academic
    fields using an injected LLM. Produces a ranked list in `candidates`
    (best-first). `chosen` mirrors the first candidate for backward-compat.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel
from pydantic import Field as PydField

from config.paths import MASTER_COLLEGE_FIELD_MAPPING_JSON
from helpers.field_helpers import FieldHelpers
from langgraph.models import Candidate, FieldClassifierInput, FieldClassifierOutput


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

    choices: List[Dict[str, str]] = PydField(
        description="List of objects: {'name': <field_name>, 'rationale': <why it fits>}."
    )


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

    def __init__(self, llm: Optional[FieldClassifierLLM] = None):
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
            The user request containing text. Optional hints may be present on
            request.meta (if your UserRequest still carries it), e.g.:
              - 'college_name'
              - 'subject'

        Returns
        -------
        FieldClassifierOutput
            Ranked `candidates` and `chosen` == top candidate for compatibility.
        """
        request = data.request

        # Safely read optional meta hints if they exist; otherwise treat as None.
        meta = getattr(request, "meta", {}) or {}
        college_name = meta.get("college_name")
        subject_hint = meta.get("subject")

        # Build candidate pool (flattened to {field: description}).
        candidates: Dict[str, str] = FieldHelpers.CollectCollegeFields(
            self.master, college_name, subject_hint
        )
        if not candidates:
            raise ValueError(
                "No fields available from master mapping. Check data/context."
            )

        candidate_names = list(candidates.keys())

        # Prompt instructs strictly-JSON returns (no prose), with up to 3 fields, best-first.
        query_text = (subject_hint or "") + "\n" + (request.text or "")
        prompt = (
            "You are an academic classifier.\n"
            "Given a research description and a list of candidate Fields, return up to 3 that best fit the topic.\n"
            "Strictly return a JSON object of the following structure:\n\n"
            "{\n"
            '  "choices": [\n'
            '     {"name": "<field name>", "rationale": "<why it fits>"}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            " - The 'name' MUST be one of the provided candidate fields (verbatim).\n"
            " - Return at most 3 choices, ordered best-first.\n"
            " - Output ONLY valid JSON. No prose, no markdown, no comments.\n\n"
            f"Research description:\n{query_text}\n\n"
            f"College (optional): {college_name or 'N/A'}\n\n"
            "Candidate Fields:\n- "
            + "\n- ".join(candidate_names[:80])  # cap list for token safety
        )

        parsed_model: Optional[LLMJsonResponse] = None

        if self.llm:
            raw = self.llm.generate_json(prompt)
            if raw:
                # Back-compat: accept {choice, rationale} and normalize to choices-list.
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
                chosen = candidate_objs[0]  # mirror top candidate for backward compat
                return FieldClassifierOutput(chosen=chosen, candidates=candidate_objs)

        # Fallback if no LLM or invalid output: choose first entry deterministically.
        fallback = Candidate(
            name=candidate_names[0],
            score=1.0,
            rationale="Fallback to first candidate; no LLM response or invalid JSON.",
        )
        return FieldClassifierOutput(chosen=fallback, candidates=[fallback])


def Build(llm: Optional[FieldClassifierLLM] = None) -> FieldClassifierNode:
    """Factory for LangGraph wiring."""
    return FieldClassifierNode(llm)