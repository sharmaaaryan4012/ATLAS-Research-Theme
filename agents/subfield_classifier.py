"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: subfield_classifier.py
Description:
    Classifies a user request into one or more subfields for a GIVEN Field.
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
from langgraph.models import Candidate, SubfieldClassifierInput, SubfieldClassifierOutput


class SubfieldClassifierLLM(Protocol):
    def generate_json(self, prompt: str) -> dict | None:
        ...


class LLMJsonResponse(BaseModel):
    choices: List[Dict[str, str]] = PydField(
        description="List of objects: {'name': <subfield_name>, 'rationale': <why it fits>}."
    )


def _load_subfield_mapping(field_name: str) -> Dict[str, str]:
    filename = f"{field_name}.json"
    path = os.path.join(FIELD_SUBFIELD_MAPPINGS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class SubfieldClassifierNode:
    def __init__(self, llm: Optional[SubfieldClassifierLLM] = None):
        self.llm = llm

    def Run(self, data: SubfieldClassifierInput) -> SubfieldClassifierOutput:
        request = data.request
        field_name = data.field_name
        if not field_name:
            raise ValueError("SubfieldClassifierNode requires `field_name` context.")

        candidates: Dict[str, str] = _load_subfield_mapping(field_name)
        if not candidates:
            raise ValueError(f"No subfields found for field '{field_name}'.")

        candidate_names = list(candidates.keys())
        query_text = request.text or ""

        prompt = (
            "You are an academic subfield classifier.\n"
            "Given a research description and a list of candidate Subfields for a GIVEN Field, "
            "return up to 3 that best fit the topic.\n"
            "Strictly return a JSON object of the following structure:\n\n"
            "{\n"
            '  \"choices\": [\n'
            '     {\"name\": \"<subfield name>\", \"rationale\": \"<why it fits>\"}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            " - The 'name' MUST be one of the provided candidate subfields (verbatim).\n"
            " - Return at most 3 choices, ordered best-first.\n"
            " - Output ONLY valid JSON. No prose, no markdown, no comments.\n\n"
            f"Top-level Field: {field_name}\n\n"
            f"Research description:\n{query_text}\n\n"
            "Candidate Subfields:\n- " + "\n- ".join(candidate_names[:80])
        )

        parsed_model: Optional[LLMJsonResponse] = None

        if self.llm:
            raw = self.llm.generate_json(prompt)
            if raw:
                if "choice" in raw and "choices" not in raw:
                    raw = {"choices": [{
                        "name": raw.get("choice", ""),
                        "rationale": raw.get("rationale", ""),
                    }]}
                try:
                    parsed_model = LLMJsonResponse(**raw)
                except Exception as e:
                    print("⚠️ Parse error in SubfieldClassifier LLM response:", e)
                    parsed_model = None

        if parsed_model and parsed_model.choices:
            valid = [c for c in parsed_model.choices if c.get("name") in candidates]
            if valid:
                candidate_objs = [
                    Candidate(name=c["name"], score=1.0, rationale=c.get("rationale", ""))
                    for c in valid
                ]
                chosen = candidate_objs[0]
                return SubfieldClassifierOutput(chosen=chosen, candidates=candidate_objs)

        # Fallback if no LLM or invalid output: choose first entry deterministically.
        fallback = Candidate(
            name=candidate_names[0],
            score=1.0,
            rationale="Fallback to first subfield; no LLM response or invalid JSON.",
        )
        return SubfieldClassifierOutput(chosen=fallback, candidates=[fallback])


def Build(llm: Optional[SubfieldClassifierLLM] = None) -> SubfieldClassifierNode:
    return SubfieldClassifierNode(llm)
