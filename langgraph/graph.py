"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: graph.py
Description:
    Minimal executable LangGraph that wires:
        Request → field_classifier → field_validator → field_enhancer → field_enhancement_validator
               → subfield_classifier → subfield_validator → END

    Enhancer/Updater branches are intentionally left disconnected.
"""

from __future__ import annotations

from . import agents as agent_factories
from .models import (
    UnitClassifierInput,
    UnitClassifierOutput,
    FieldClassifierInput,
    FieldEnhancementValidatorInput,
    FieldEnhancerInput,
    FieldValidatorInput,
    SubfieldClassifierInput,
    SubfieldValidatorInput,
    UnitValidatorInput,
    UserRequest,
)
from .state import State


class Graph:
    def __init__(
        self,
        unit_classifier_llm=None,
        unit_validator_llm=None,
        field_classifier_llm=None,
        field_validator_llm=None,
        field_enhancer_llm=None,
        field_enhancement_validator_llm=None,
        subfield_classifier_llm=None,
        subfield_validator_llm=None,
    ):
        self.unit_classifier = agent_factories.BuildUnitClassifier(
            unit_classifier_llm
        )
        self.unit_validator = agent_factories.BuildUnitValidator(
            unit_validator_llm
        )
        self.field_classifier = agent_factories.BuildFieldClassifierAgent(
            field_classifier_llm
        )
        self.field_enhancer = agent_factories.BuildFieldEnhancerAgent(
            field_enhancer_llm
        )
        self.field_enhancement_validator = agent_factories.BuildFieldEnhancementValidatorAgent(
                field_enhancement_validator_llm
        )
        
        self.field_validator = agent_factories.BuildFieldValidatorAgent(
            field_validator_llm
        )
        self.subfield_classifier = agent_factories.BuildSubfieldClassifierAgent(
            subfield_classifier_llm
        )
        self.subfield_validator = agent_factories.BuildSubfieldValidatorAgent(
            subfield_validator_llm
        )

    def Run(self, request: UserRequest) -> State:
        state = State(request=request)

        state = self.RunUnitStage(state)

        state = self.RunFieldStage(state)

        state = self.RunSubfieldStage(state)

        state.record("end")

        return state
    
    # WORK FOR UNITS
    def RunUnitStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_units = False
        while (not valid_units) and n_iterations <= max_iterations:
            state = self.UnitClassification(state)
            state = self.UnitValidation(state)
            valid_units = state.unit_satisfaction == "satisfied"
            n_iterations += 1

        return state
    
    def UnitClassification(self, state: State):
        state.record("enter_unit_classifier")
        output_valid = False
        iterations = 1
        while (not output_valid) and iterations <= 3:
            uc_out = self.unit_classifier.Run(
                UnitClassifierInput(
                    request=state.request, feedback=state.unit_validation
                )
            )
            state.units = uc_out.candidates
            output_valid = uc_out.output_valid
            if output_valid:
                state.record(
                    "unit_classifier_done",
                    candidates=[c.name for c in uc_out.candidates],
                )
            iterations += 1
        if not output_valid:
            raise ValueError("Unable to parse LLM output. No units identified.")
        return state

    def UnitValidation(self, state: State):
        # 2) Unit Validator ----------------------------------------------------
        state.record("enter_unit_validator")
        uv_out = self.unit_validator.Run(
            UnitValidatorInput(
                unit_names=state.get_units(),
                request=state.request,
                feedback=state.unit_validation,
            )
        )
        state.unit_validation = uv_out.report
        state.unit_satisfaction = uv_out.satisfaction
        state.record(
            "unit_validator_done",
            is_valid=uv_out.report.is_valid,
            reason=uv_out.report.reason,
            removals=uv_out.report.removals,
            additions=uv_out.report.removals,
            satisfaction=uv_out.satisfaction,
        )

        return state


    # WORK FOR FIELDS
    def RunFieldStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_fields = False
        while (not valid_fields) and n_iterations <= max_iterations:
            state = self.FieldClassification(state)
            state = self.FieldValidation(state)
            valid_fields = state.field_satisfaction == "satisfied"
            n_iterations += 1

        state = self.FieldEnhancement(state)
        state = self.FieldEnhancementValidation(state)

        return state

    def FieldClassification(self, state: State):
        state.record("enter_field_classifier")
        output_valid = False
        iterations = 1
        while (not output_valid) and iterations <= 3:
            fc_out = self.field_classifier.Run(
                FieldClassifierInput(
                    request=state.request, unit_names = state.get_units(), feedback=state.field_validation
                )
            )
            state.fields = fc_out.candidates
            output_valid = fc_out.output_valid
            if output_valid:
                state.record(
                    "field_classifier_done",
                    candidates=[c.name for c in fc_out.candidates],
                )
            iterations += 1
        if not output_valid:
            raise ValueError("Unable to parse LLM output. No fields identified.")
        return state

    def FieldValidation(self, state: State):
        # 2) FIELD VALIDATOR ----------------------------------------------------
        state.record("enter_field_validator")
        fv_out = self.field_validator.Run(
            FieldValidatorInput(
                field_names=state.get_fields(),
                unit_names=state.get_units(),
                request=state.request,
                feedback=state.field_validation,
            )
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

    def FieldEnhancement(self, state: State):
        state.record("enter_field_enhancer")
        fe_out = self.field_enhancer.Run(
            FieldEnhancerInput(request=state.request, unit_names = state.get_units(), feedback=state.field_validation)
        )
        state.new_fields = fe_out.proposed_candidates
        state.record(
            "field_enhancer_done",
            candidates=state.get_new_fields(),
        )
        return state

    def FieldEnhancementValidation(self, state: State):
        state.record("enter_field_enhancement_validator")
        fev_out = self.field_enhancement_validator.Run(
            FieldEnhancementValidatorInput(
                request=state.request, unit_names = state.get_units(), new_field_names=state.get_new_fields()
            )
        )
        suggested_fields = state.get_new_fields()
        # update the new fields
        if not fev_out.satisfaction:
            removals = fev_out.report.removals
            for r in removals:
                    suggested_fields.remove(r)
        state.new_fields = [f for f in state.new_fields if f.name in  suggested_fields]
        state.record(
            "field_enhancement_validator_done",
            candidates=state.get_new_fields(),
        )
        return state

    # WORK FOR SUBFIELDS
    def RunSubfieldStage(self, state: State):
        max_iterations = 3
        n_iterations = 1
        valid_subfields = False
        while (not valid_subfields) and n_iterations <= max_iterations:
            state = self.SubfieldClassification(state)
            state = self.SubfieldValidation(state)
            valid_subfields = state.subfield_satisfaction == "satisfied"
            n_iterations += 1
        return state

    def SubfieldClassification(self, state: State):
        # 3) Subfield Classifier -----------------------------------------------
        state.record("enter_subfield_classifier")
        output_valid = False
        iterations = 1
        while (not output_valid) and iterations <= 3:
            sc_out = self.subfield_classifier.Run(
                SubfieldClassifierInput(
                    request=state.request,
                    field_names=state.get_fields(),
                    feedback=state.subfield_validation,
                )
            )
            state.subfields = sc_out.candidates
            output_valid = sc_out.output_valid
            if output_valid:
                state.record(
                    "subfield_classifier_done",
                    candidates=[c.name for c in sc_out.candidates],
                )
            iterations += 1
        if not output_valid:
            raise ValueError(
                "Unable to parse LLM output. Identified Fields were: ",
                state.get_fields(),
                ". New field suggestions were: ",
                state.get_new_fields(),
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
                feedback=state.subfield_validation,
            )
        )
        state.subfield_validation = sv_out.report
        state.subfield_satisfaction = sv_out.satisfaction
        state.record(
            "subfield_validator_done",
            is_valid=sv_out.report.is_valid,
            reason=sv_out.report.reason,
            removals=sv_out.report.removals,
            additions=sv_out.report.additions,
            satisfaction=sv_out.satisfaction,
        )
        return state


def BuildGraph(
    unit_classifier_llm=None,
    unit_validator_llm=None,
    field_classifier_llm=None,
    field_validator_llm=None,
    field_enhancer_llm=None,
    field_enhancement_validator_llm=None,
    subfield_classifier_llm=None,
    subfield_validator_llm=None,
) -> Graph:
    return Graph(
        unit_classifier_llm=unit_classifier_llm,
        unit_validator_llm=unit_validator_llm,
        field_classifier_llm=field_classifier_llm,
        field_validator_llm=field_validator_llm,
        field_enhancer_llm=field_enhancer_llm,
        field_enhancement_validator_llm=field_enhancement_validator_llm,
        subfield_classifier_llm=subfield_classifier_llm,
        subfield_validator_llm=subfield_validator_llm,
    )
