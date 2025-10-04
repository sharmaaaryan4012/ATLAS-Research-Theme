"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS - Research Theme
File: checkMappingDiscrepency.py
Description: Compares MasterCollegeFieldMapping.json and MasterFieldSubfieldMapping.json
             to find mismatches (missing/extra colleges, departments, fields),
             and validate subfield structure (new style).

New style notes:
- MasterCollegeFieldMapping.json:
    college -> department -> dict(field -> description) OR str(dept description)
- MasterFieldSubfieldMapping.json:
    college -> department -> field -> dict(subfield -> description)
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from config.paths import (
        MASTER_COLLEGE_FIELD_MAPPING_JSON,
        MASTER_FIELD_SUBFIELD_MAPPING_JSON,
    )
except Exception as e:
    print(
        "ERROR: Could not import from config.paths. "
        "Run from project root or use `python -m misc.checkMappingDiscrepency`.\n"
        f"Details: {e}"
    )
    sys.exit(1)

MASTER_CF = MASTER_COLLEGE_FIELD_MAPPING_JSON
MASTER_FS = MASTER_FIELD_SUBFIELD_MAPPING_JSON


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_cf_fields(cf):
    """
    From MasterCollegeFieldMapping (new style) produce:
    { college: { dept: set(fields) } }
    Departments with only descriptions (no fields) map to empty sets.
    """
    out = {}
    for college, dept_obj in cf.items():
        out[college] = {}
        if isinstance(dept_obj, dict):
            for dept, maybe_fields in dept_obj.items():
                if isinstance(maybe_fields, dict):
                    out[college][dept] = set(maybe_fields.keys())
                else:
                    out[college][dept] = set()
        else:
            out[college] = {}
    return out


def extract_fs_fields(fs):
    """
    From MasterFieldSubfieldMapping (new style) produce:
    { college: { dept: set(fields) } }
    """
    out = {}
    for college, dept_obj in fs.items():
        out[college] = {}
        if isinstance(dept_obj, dict):
            for dept, field_obj in dept_obj.items():
                if isinstance(field_obj, dict):
                    out[college][dept] = set(field_obj.keys())
                else:
                    out[college][dept] = set()
        else:
            out[college] = {}
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Check discrepancies between master mappings (new style)."
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with non-zero status code if any issues are found.",
    )
    parser.add_argument(
        "--report-json",
        type=str,
        default=None,
        help="Optional path to write a JSON report.",
    )
    args = parser.parse_args()

    issues = defaultdict(list)

    if not os.path.isfile(MASTER_CF):
        print(f"ERROR: Master college-field mapping not found at: {MASTER_CF}")
        sys.exit(1)
    if not os.path.isfile(MASTER_FS):
        print(f"ERROR: Master field-subfield mapping not found at: {MASTER_FS}")
        sys.exit(1)

    cf = load_json(MASTER_CF)  # college -> dept -> (fields dict | description)
    fs = load_json(MASTER_FS)  # college -> dept -> field -> subfield dict

    # Colleges present
    cf_colleges = set(cf.keys())
    fs_colleges = set(fs.keys())

    missing_in_fs = sorted(cf_colleges - fs_colleges)
    extra_in_fs = sorted(fs_colleges - cf_colleges)

    if missing_in_fs:
        issues["missing_colleges_in_field_subfield"].extend(missing_in_fs)
    if extra_in_fs:
        issues["extra_colleges_in_field_subfield"].extend(extra_in_fs)

    # Normalize to {college: {dept: set(fields)}}
    cf_norm = extract_cf_fields(cf)
    fs_norm = extract_fs_fields(fs)

    # Departments & Fields
    for college in sorted(cf_colleges | fs_colleges):
        cf_depts = set(cf_norm.get(college, {}).keys())
        fs_depts = set(fs_norm.get(college, {}).keys())

        missing_depts_in_fs = sorted(cf_depts - fs_depts)
        extra_depts_in_fs = sorted(fs_depts - cf_depts)

        if missing_depts_in_fs:
            issues["missing_departments_in_field_subfield"].append(
                {"college": college, "departments": missing_depts_in_fs}
            )
        if extra_depts_in_fs:
            issues["extra_departments_in_field_subfield"].append(
                {"college": college, "departments": extra_depts_in_fs}
            )

        for dept in sorted(cf_depts | fs_depts):
            cf_fields = cf_norm.get(college, {}).get(dept, set())
            fs_fields = fs_norm.get(college, {}).get(dept, set())

            missing_fields_in_fs = sorted(cf_fields - fs_fields)
            extra_fields_in_fs = sorted(fs_fields - cf_fields)

            if missing_fields_in_fs:
                issues["missing_fields_in_field_subfield"].append(
                    {
                        "college": college,
                        "department": dept,
                        "fields": missing_fields_in_fs,
                    }
                )
            if extra_fields_in_fs:
                issues["extra_fields_in_field_subfield"].append(
                    {
                        "college": college,
                        "department": dept,
                        "fields": extra_fields_in_fs,
                    }
                )

            # Validate FS subfield structure & duplicates
            if dept in fs.get(college, {}):
                field_obj = fs.get(college, {}).get(dept, {})
                if isinstance(field_obj, dict):
                    for field, subfield_obj in field_obj.items():
                        if not isinstance(subfield_obj, dict):
                            issues["invalid_subfield_type"].append(
                                {
                                    "college": college,
                                    "department": dept,
                                    "field": field,
                                    "detail": f"Expected dict(subfield->desc), got {type(subfield_obj).__name__}",
                                }
                            )
                        else:
                            # Check keys (names) and values (descriptions)
                            subfields = list(subfield_obj.keys())
                            # duplicate names?
                            if len(subfields) != len(set(subfields)):
                                issues["duplicate_subfields"].append(
                                    {
                                        "college": college,
                                        "department": dept,
                                        "field": field,
                                    }
                                )
                            # empty?
                            if len(subfields) == 0:
                                issues["empty_subfields"].append(
                                    {
                                        "college": college,
                                        "department": dept,
                                        "field": field,
                                    }
                                )
                            # description type
                            bad_desc = [
                                k
                                for k, v in subfield_obj.items()
                                if not isinstance(v, str)
                            ]
                            if bad_desc:
                                issues["invalid_subfield_description_type"].append(
                                    {
                                        "college": college,
                                        "department": dept,
                                        "field": field,
                                        "subfields": bad_desc,
                                    }
                                )

    # Print summary
    has_issues = any(len(v) > 0 for v in issues.values())
    if has_issues:
        print("\n=== DISCREPANCY REPORT ===")
        for key in sorted(issues.keys()):
            print(f"\n- {key}:")
            for item in issues[key]:
                print(f"  • {item}")
    else:
        print("No discrepancies found. ✅")

    # Optional JSON report
    if args.report_json:
        os.makedirs(os.path.dirname(args.report_json), exist_ok=True)
        with open(args.report_json, "w", encoding="utf-8") as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
        print(f"\nReport written to: {args.report_json}")

    if args.fail_on_issues and has_issues:
        sys.exit(2)


if __name__ == "__main__":
    main()
