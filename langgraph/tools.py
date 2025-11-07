"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: tools.py
Description: Implementation of various tools used in the Graph.
"""

from __future__ import annotations
from typing import Any


class NoopTool:
    """Placeholder tool that does nothing but record the intent."""

    def __init__(self, name: str):
        self.name = name

    def Run(self, data: Any) -> Any:
        return {"tool": self.name, "status": "skipped"}


def BuildFieldUpdaterTool():
    return NoopTool("field_updater")


def BuildSubfieldUpdaterTool():
    return NoopTool("subfield_updater")
