from typing import Literal, Dict, Any
import sys, pathlib

# --- bootstrap import path ---
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import paths  # fine to keep if you use elsewhere

from lg.state import State
from lg.tools import generator_prompt, reflector_prompt
from lg.agents import (
    field_generator_node, field_reflector_node,
    subfield_generator_node, subfield_reflector_node
)
from models.request import UserRequest
from models.classification import ClassificationBundle


def print_classification(state: State, location: str):
    classification_bundle = state["classification_bundle"]
    fields = classification_bundle.fields
    satisfied_fields = classification_bundle.satisfied_fields
    subfields = classification_bundle.subfields
    satisfied_subfields = classification_bundle.satisfied_subfields
    print("At ", location)
    print("Fields: ", fields.field_names)
    print("Satisfied with Fields: ", satisfied_fields)
    print("Subfields: ", subfields.subfield_names)
    print("Satisfied with Subfields: ", satisfied_subfields)


# ---------------------------
# Pipeline step functions
# ---------------------------
def field_classifier(state: State) -> Dict[str, Any]:
    print_classification(state, "field classifier")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields_classification = classification_bundle.fields
    fields_to_remove = fields_classification.fields_to_remove  # after reflection

    prompt = generator_prompt(
        research_description=research_description,
        department=department,
        remove=fields_to_remove
    )
    return {"messages": [prompt]}


def field_validator(state: State) -> Dict[str, Any]:
    print_classification(state, "field validator")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields_classification = classification_bundle.fields
    classification = fields_classification.field_names
    fields_to_remove = fields_classification.fields_to_remove

    prompt = reflector_prompt(
        research_description=research_description,
        department=department,
        classification=classification,
        remove=fields_to_remove
    )
    return {"messages": [prompt]}


def subfield_classifier(state: State) -> Dict[str, Any]:
    print_classification(state, "subfield classifier")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields = classification_bundle.fields.field_names
    subfields_classification = classification_bundle.subfields
    subfields_to_remove = subfields_classification.subfields_to_remove

    prompt = generator_prompt(
        research_description=research_description,
        department=department,
        fields=fields,
        remove=subfields_to_remove
    )
    return {"messages": [prompt]}


def subfield_validator(state: State) -> Dict[str, Any]:
    print_classification(state, "subfield validator")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields = classification_bundle.fields.field_names
    subfields_classification = classification_bundle.subfields
    classification = subfields_classification.subfield_names
    subfields_to_remove = subfields_classification.subfields_to_remove

    prompt = reflector_prompt(
        research_description=research_description,
        department=department,
        classification=classification,
        fields=fields,
        remove=subfields_to_remove
    )
    return {"messages": [prompt]}


# ---------------------------
# Minimal orchestrator (no LangGraph)
# ---------------------------
def run_pipeline(start_state: State,
                 max_field_iters: int = 5,
                 max_subfield_iters: int = 5) -> State:
    """
    Runs: (field classify -> generate -> validate -> reflect)* until satisfied_fields
          then (subfield classify -> generate -> validate -> reflect)* until satisfied_subfields.
    Each step function returns a partial dict to merge into `state` (like LangGraph nodes).
    Agent nodes (e.g., *_generator_node / *_reflector_node) are expected to
    update `classification_bundle` and/or `messages`.
    """
    # make a shallow copy so caller's dict isn't mutated unexpectedly
    state: State = dict(start_state)

    def apply(step_fn):
        updates = step_fn(state) or {}
        state.update(updates)

    # ----- fields loop -----
    for _ in range(max_field_iters):
        apply(field_classifier)
        apply(field_generator_node)   # agent uses state["messages"] and updates bundle
        apply(field_validator)
        apply(field_reflector_node)   # sets fields_to_remove / satisfied_fields, etc.
        if state["classification_bundle"].satisfied_fields:
            break

    # ----- subfields loop -----
    for _ in range(max_subfield_iters):
        apply(subfield_classifier)
        apply(subfield_generator_node)
        apply(subfield_validator)
        apply(subfield_reflector_node)
        if state["classification_bundle"].satisfied_subfields:
            break

    return state


# ---------------------------
# Example run
# ---------------------------
if __name__ == "__main__":
    faculty_description = """US imperialism; race's relationship to gender and sexuality; climate

    My research takes transimperial, interimperial, and international approaches. In my first book I examined the intersections of settler colonialism and Black removal efforts (e.g. Liberian colonization), illuminating the centrality of languages of climate, race, and gender to intellectual debates over geographies of Black freedom.

    My other works include peer-reviewed articles on the U.S. opening of Japan and how it generated imaginings of difference and affinity that unsettled the Black-white dichotomy and the binarized correspondence of gender and sexuality dominating popular discourse in the U.S. East. 

    I am currently working on a book manuscript on U.S. imperialism in the Pacific up to the end of the Philippine-American War.
    """

    department = "History"

    user_request = UserRequest()
    user_request.research_description = faculty_description
    user_request.department = department

    start_state: State = {
        "messages": [],
        "user_request": user_request,
        "classification_bundle": ClassificationBundle(),
    }

    print(start_state["user_request"])
    final_state = run_pipeline(start_state)
    print_classification(final_state, "END RESULTS")
