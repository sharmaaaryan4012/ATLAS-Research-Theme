import json
import os
from typing import Dict, List, Optional, Protocol

from config.paths import COLLEGE_FIELD_MAPPINGS_DIR, FIELD_SUBFIELD_MAPPINGS_DIR


def _load_field_mapping(
    college: str, department: str, removals: List[str], additions: List[str]
) -> Dict[str, str]:
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
                        if r in department_data:
                            del department_data[r]
                if additions is not None:
                    for a in additions:
                        if a not in department_data:
                            # ask llm to output a description if suggesting
                            department_data[a] = ""
            except Exception as e:
                raise ValueError(
                    'Invalid department name: "' + department + '" does not exist.'
                )
    except Exception as e:
        raise ValueError('Invalid college name: "' + college + '" does not exist.')
    return department_data


def _load_subfield_mapping(
    field_names: List[str], removals: List[str], additions: List[str]
) -> Dict[str, str]:
    subfield_descriptions = {}
    for f in field_names:
        filename = f"{f}.json"
        try:
            path = os.path.join(FIELD_SUBFIELD_MAPPINGS_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                subfield_data = json.load(f)
                subfield_descriptions = subfield_descriptions | subfield_data
        except Exception as e:
            raise ValueError("Error while loading subfields of field: " + f + ".")
    if removals is not None:
        for r in removals:
            if r in subfield_descriptions:
                del subfield_descriptions[r]
    if additions is not None:
        for a in additions:
            if a not in subfield_descriptions:
                subfield_descriptions[a] = ""
    return subfield_descriptions
