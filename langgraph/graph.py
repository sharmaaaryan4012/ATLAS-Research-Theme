"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: graph.py
Description:
    Minimal executable LangGraph that wires:
        Request → field_classifier → field_validator
               → subfield_classifier → subfield_validator → END

    Enhancer/Updater branches are intentionally left disconnected.
"""

from __future__ import annotations

from .models import (
    FieldClassifierInput,
    FieldValidatorInput,
    Satisfaction,
    SubfieldClassifierInput,
    SubfieldValidatorInput,
    UserRequest,
)
from .state import State
from . import agents as agent_factories


class Graph:
    def __init__(
        self,
        field_classifier_llm=None,
        field_validator_llm=None,
        subfield_classifier_llm=None,
        subfield_validator_llm=None,
    ):
        self.field_classifier = agent_factories.BuildFieldClassifierAgent(field_classifier_llm)
        self.field_validator = agent_factories.BuildFieldValidatorAgent(field_validator_llm)
        self.subfield_classifier = agent_factories.BuildSubfieldClassifierAgent(subfield_classifier_llm)
        self.subfield_validator = agent_factories.BuildSubfieldValidatorAgent(subfield_validator_llm)

    def Run(self, request: UserRequest) -> State:
        state = State(request=request)
        # print(state)
        state = self.RunFieldStage(state)

        state = self.RunSubfieldStage(state)

        state.record("end")

        return state

    # WORK FOR FIELDS 
    def RunFieldStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_fields = False
        while not valid_fields and n_iterations <= max_iterations:
            state = self.FieldClassification(state)
            state = self.FieldValidation(state)
            valid_fields = state.field_satisfaction == "satisfied"
            n_iterations += 1
        print(state.get_fields())
        return state
    
    def FieldClassification(self, state: State):
        state.record("enter_field_classifier")
        fc_out = self.field_classifier.Run(FieldClassifierInput(request=state.request, feedback = state.field_validation))
        state.fields = fc_out.candidates
        state.record(
            "field_classifier_done",
            candidates=[c.name for c in fc_out.candidates],
        )
        return state
    
    def FieldValidation(self, state: State):
        # 2) FIELD VALIDATOR ----------------------------------------------------
        state.record("enter_field_validator")
        fv_out = self.field_validator.Run(
            FieldValidatorInput(field_names=state.get_fields(), request=state.request, feedback = state.field_validation)
        )
        state.field_validation = fv_out.report
        state.field_satisfaction = fv_out.satisfaction
        state.record(
            "field_validator_done",
            is_valid=fv_out.report.is_valid,
            reason=fv_out.report.reason,
            removals=fv_out.report.removals,
            additions=fv_out.report.removals,
            satisfaction=fv_out.satisfaction,
        )
        
        return state

    # WORK FOR SUBFIELDS    
    def RunSubfieldStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_subfields = False
        while not valid_subfields and n_iterations <= max_iterations:
            state = self.SubfieldClassification(state)
            state = self.SubfieldValidation(state)
            valid_subfields = state.subfield_satisfaction == "satisfied"
            n_iterations += 1
        print(state.get_subfields())
        return state
    
    def SubfieldClassification(self, state: State):
        # 3) Subfield Classifier -----------------------------------------------
        state.record("enter_subfield_classifier")
        sc_out = self.subfield_classifier.Run(
            SubfieldClassifierInput(request=state.request, field_names = state.get_fields(), feedback = state.subfield_validation)
        )
        state.subfields = sc_out.candidates
        state.record(
            "subfield_classifier_done",
            candidates=[c.name for c in sc_out.candidates],
        )
        return state

    def SubfieldValidation(self, state: State):
        # 4) Subfield Validator -------------------------------------------------
        state.record("enter_subfield_validator")
        sv_out = self.subfield_validator.Run(
            SubfieldValidatorInput(
                subfield_names=state.get_subfields(),
                field_names=state.get_fields(),
                request=state.request,
                feedback = state.subfield_validation
            )
        )
        state.subfield_validation = sv_out.report
        state.subfield_satisfaction = sv_out.satisfaction
        state.record(
            "subfield_validator_done",
            is_valid=sv_out.report.is_valid,
            reason=sv_out.report.reason,
            removals=sv_out.report.removals,
            additions = sv_out.report.additions,
            satisfaction=sv_out.satisfaction,
        )
        return state


def BuildGraph(
    field_classifier_llm=None,
    field_validator_llm=None,
    subfield_classifier_llm=None,
    subfield_validator_llm=None,
) -> Graph:
    return Graph(
        field_classifier_llm=field_classifier_llm,
        field_validator_llm=field_validator_llm,
        subfield_classifier_llm=subfield_classifier_llm,
        subfield_validator_llm=subfield_validator_llm,
    )
