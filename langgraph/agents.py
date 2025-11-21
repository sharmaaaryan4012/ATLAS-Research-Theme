"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: agents.py
Description: Implementation of various agents used in the Graph.
"""

from __future__ import annotations

from typing import Optional

from agents.unit_classifier import Build as BuildUnitClassifier
from agents.unit_validator import Build as BuildUnitValidator
from agents.field_classifier import Build as BuildFieldClassifier
from agents.field_enhancement_validator import Build as BuildFieldEnhancementValidator
from agents.field_enhancer import Build as BuildFieldEnhancer
from agents.field_validator import Build as BuildFieldValidator
from agents.subfield_classifier import Build as BuildSubfieldClassifier
from agents.subfield_validator import Build as BuildSubfieldValidator

def BuildUnitClassifierAgent(llm=None):
    return BuildUnitClassifier(llm)


def BuildUnitValidatorAgent(llm=None):
    return BuildUnitValidator(llm)


def BuildFieldClassifierAgent(llm=None):
    return BuildFieldClassifier(llm)


def BuildFieldValidatorAgent(llm=None):
    return BuildFieldValidator(llm)


def BuildFieldEnhancerAgent(llm=None):
    return BuildFieldEnhancer(llm)


def BuildFieldEnhancementValidatorAgent(llm=None):
    return BuildFieldEnhancementValidator(llm)


def BuildSubfieldClassifierAgent(llm=None):
    return BuildSubfieldClassifier(llm)


def BuildSubfieldValidatorAgent(llm=None):
    return BuildSubfieldValidator(llm)
