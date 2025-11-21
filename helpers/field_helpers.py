import json
import os
from typing import Dict, List, Optional, Protocol
import re

from config.paths import COLLEGE_FIELD_MAPPINGS_DIR, FIELD_SUBFIELD_MAPPINGS_DIR

def _load_units(
        college: str, removals: List[str], additions: List[str]
) -> List[str]:
    """
    Returns
    --------
     List[str]: units under college
    """ 
    filename = f"{college}.json"
    path = os.path.join(COLLEGE_FIELD_MAPPINGS_DIR, filename)
    units_list = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            college_data = json.load(f)
            units_list = college_data.keys()
            if removals is not None:
                for r in removals:
                    units_list = [unit for unit in units_list if unit != r]
            if additions is not None:
                for a in additions:
                    units_list.append(a)
    except Exception as e:
            raise ValueError('Invalid college name: "' + college + '" does not exist.')
    return units_list

def _load_field_mapping(
    college: str, units: List[str], removals: List[str], additions: List[str]
) -> Dict[str, str]:
    """
    Returns
    --------
     Dict[str, str]: programs under selected units and their descriptions
    """
    filename = f"{college}.json"
    path = os.path.join(COLLEGE_FIELD_MAPPINGS_DIR, filename)
    programs_dict = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            college_data = json.load(f)
            try:
                for u in units:
                    unit_data = college_data[u]
                    if removals is not None:
                        for r in removals:
                            if r in unit_data:
                                del unit_data[r]
                    programs_dict = programs_dict | unit_data
            except Exception as e:
                raise ValueError(
                    'Invalid unit name: "' + u + '" does not exist.'
                )
        if additions is not None:
            for a in additions:
                if a not in programs_dict:
                    # ask llm to output a description if suggesting
                    programs_dict[a] = ""
    except Exception as e:
        raise ValueError('Invalid college name: "' + college + '" does not exist.')
    return programs_dict


def _load_subfield_mapping(
    field_names: List[str], removals: List[str], additions: List[str]
) -> Dict[str, str]:
    subfield_descriptions = {}
    for f in field_names:
        cleaned_program = re.sub(r"[^\w\s\-\(\)&,\.]", "_", f, flags=re.UNICODE)
        cleaned_program = re.sub(r"\s+", " ", cleaned_program).strip()
        filename = f"{cleaned_program}.json"
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
