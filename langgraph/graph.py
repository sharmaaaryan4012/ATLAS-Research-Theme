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

        self.RunFieldStage(state)

        self.RunSubfieldStage(state)

        state.record("end")

        return

        if fv_out.satisfaction == Satisfaction.Unsatisfied:
            state.record("stop_after_field_validation", reason=fv_out.report.reason)
            return state

        # 3) SUBFIELD CLASSIFIER -----------------------------------------------
        state.record("enter_subfield_classifier")
        sc_out = self.subfield_classifier.Run(
            SubfieldClassifierInput(request=request, field_name=fc_out.chosen.name)
        )
        state.subfield_candidates = sc_out.candidates
        state.chosen_subfield = sc_out.chosen
        state.record(
            "subfield_classifier_done",
            chosen=sc_out.chosen.name,
            candidates=[c.name for c in sc_out.candidates],
        )

        # 4) SUBFIELD VALIDATOR -------------------------------------------------
        state.record("enter_subfield_validator")
        sv_out = self.subfield_validator.Run(
            SubfieldValidatorInput(
                subfield_name=sc_out.chosen.name,
                field_name=fc_out.chosen.name,
                request=request,
            )
        )
        state.subfield_validation = sv_out.report
        state.subfield_satisfaction = sv_out.satisfaction
        state.record(
            "subfield_validator_done",
            is_valid=sv_out.report.is_valid,
            reason=sv_out.report.reason,
            suggestions=sv_out.report.suggestions,
            satisfaction=sv_out.satisfaction,
        )

        state.record("end")
        return state
    
    def RunFieldStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_fields = False
        while not valid_fields and n_iterations <= max_iterations:
            state = self.FieldClassification(state)
            state = self.FieldValidation(state)
            valid_fields = state.field_satisfaction == "satisfied"
            n_iterations += 1
        return state
    
    def FieldClassification(self, state: State):
        state.record("enter_field_classifier")
        fc_out = self.field_classifier.Run(FieldClassifierInput(request=state["request"]))
        state.field_candidates = fc_out.candidates
        state.record(
            "field_classifier_done",
            candidates=[c.name for c in fc_out.candidates],
        )
        return state
    
    def FieldValidation(self, state: State):
        # 2) FIELD VALIDATOR ----------------------------------------------------
        state.record("enter_field_validator")
        fv_out = self.field_validator.Run(
            FieldValidatorInput(fields=state.field_candidates, request=state["request"])
        )
        state.field_validation = fv_out.report
        state.field_satisfaction = fv_out.satisfaction
        state.record(
            "field_validator_done",
            is_valid=fv_out.report.is_valid,
            reason=fv_out.report.reason,
            removals=fv_out.report.removals,
            satisfaction=fv_out.satisfaction,
        )

        
    def RunSubfieldStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_subfields = False
        while not valid_subfields and n_iterations <= max_iterations:
            state = self.SubfieldClassification(state)
            state = self.SubfieldValidation(state)
            valid_subfields = state.subfield_satisfaction == "satisfied"
            n_iterations += 1
        return state
    
    def SubfieldClassification(self, state: State):
        # 3) SUBFIELD CLASSIFIER -----------------------------------------------
        state.record("enter_subfield_classifier")
        sc_out = self.subfield_classifier.Run(
            SubfieldClassifierInput(request=state["request"], field_names = fc_out.chosen.name)
        )
        state.subfield_candidates = sc_out.candidates
        state.chosen_subfield = sc_out.chosen
        state.record(
            "subfield_classifier_done",
            chosen=sc_out.chosen.name,
            candidates=[c.name for c in sc_out.candidates],
        )

    def SubfieldValidation(self, state: State):
        # 4) SUBFIELD VALIDATOR -------------------------------------------------
        state.record("enter_subfield_validator")
        sv_out = self.subfield_validator.Run(
            SubfieldValidatorInput(
                subfield_name=sc_out.chosen.name,
                field_name=fc_out.chosen.name,
                request=state["request"],
            )
        )
        state.subfield_validation = sv_out.report
        state.subfield_satisfaction = sv_out.satisfaction
        state.record(
            "subfield_validator_done",
            is_valid=sv_out.report.is_valid,
            reason=sv_out.report.reason,
            suggestions=sv_out.report.suggestions,
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
