from typing import Dict, List, Optional, Protocol
import json
import os

from config.paths import COLLEGE_FIELD_MAPPINGS_DIR
from config.paths import FIELD_SUBFIELD_MAPPINGS_DIR

def _load_field_mapping(college: str, department: str, removals: List[str], additions: List[str]) -> Dict[str, str]:
    """
    Returns
    --------
     Dict[str, str]: fields under college/department and their descriptions
    """
    filename = f"{college}.json"
    path = os.path.join(COLLEGE_FIELD_MAPPINGS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            college_data = json.load(f)
            try:
                department_data = college_data[department]
                if removals is not None:
                    for r in removals:
                        del department_data[r]
                if additions is not None:
                    for a in additions:
                        # ask llm to output a description if suggesting
                        department_data[a] = ""
            except Exception as e:
                raise ValueError("Invalid department name: \"" + department + "\" does not exist.")
    except Exception as e:
        raise ValueError("Invalid college name: \"" + college + "\" does not exist.")


def _load_subfield_mapping(field_names: List[str]) -> Dict[str, str]:
    for f in field_names: 
    filename = f"{field_name}.json"
    path = os.path.join(FIELD_SUBFIELD_MAPPINGS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        field_data json.load(f)