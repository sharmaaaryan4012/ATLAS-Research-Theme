from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List




@dataclass
class UserRequest:
    """Container for the inbound classification request.


    TODO:
    - Add request source metadata (e.g., professor profile URL, PDF, free-text prompt).
    - Enforce validation/normalization (strip, lower for some fields, etc.).
    """


    raw_text: str
    request_id: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


def IsEmpty(self) -> bool:
    """Return True if the raw_text is empty after normalization."""
    # TODO: normalization rules (punctuation, whitespace collapse, etc.)
    return len(self.raw_text.strip()) == 0