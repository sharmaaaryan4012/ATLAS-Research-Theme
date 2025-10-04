"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS - Research Theme
File: checkMappingDiscrepency.py
Description: Compares MasterCollegeFieldMapping.json and MasterFieldSubfieldMapping.json
             to find any mismatches (missing/extra colleges, departments, fields),
             and basic validation of subfield lists.
"""

from pathlib import Path
import json
import os
import sys
import argparse
from collections import defaultdict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from config.paths import (
        DATA_CONTEXT_DIR,
        MASTER_COLLEGE_FIELD_MAPPING_JSON,
        MASTER_FIELD_SUBFIELD_MAPPING_JSON,
    )
except Exception as e:
    print("ERROR: Could not import from config.paths. "
          "Ensure you run from project root or use `python -m misc.checkMappingDiscrepency`.\n"
          f"Details: {e}")
    sys.exit(1)

MASTER_CF = MASTER_COLLEGE_FIELD_MAPPING_JSON
MASTER_FS = MASTER_FIELD_SUBFIELD_MAPPING_JSON


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Check discrepancies between master college-field and field-subfield mappings.")
    parser.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero status code if any issues are found.")
    parser.add_argument("--report-json", type=str, default=None,
                        help="Optional path to write a JSON report.")
    args = parser.parse_args()

    issues = defaultdict(list)

    if not os.path.isfile(MASTER_CF):
        print(f"ERROR: Master college-field mapping not found at: {MASTER_CF}")
        sys.exit(1)
    if not os.path.isfile(MASTER_FS):
        print(f"ERROR: Master field-subfield mapping not found at: {MASTER_FS}")
        sys.exit(1)

    cf = load_json(MASTER_CF)  # college -> dept -> [fields]
    fs = load_json(MASTER_FS)  # college -> dept -> field -> [subfields]

    # 1) Colleges present
    cf_colleges = set(cf.keys())
    fs_colleges = set(fs.keys())

    missing_in_fs = sorted(cf_colleges - fs_colleges)
    extra_in_fs = sorted(fs_colleges - cf_colleges)

    if missing_in_fs:
        issues["missing_colleges_in_field_subfield"].extend(missing_in_fs)
    if extra_in_fs:
        issues["extra_colleges_in_field_subfield"].extend(extra_in_fs)

    # 2) Departments & Fields
    for college in sorted(cf_colleges | fs_colleges):
        cf_depts = set(cf.get(college, {}).keys()) if isinstance(cf.get(college), dict) else set()
        fs_depts = set(fs.get(college, {}).keys()) if isinstance(fs.get(college), dict) else set()

        missing_depts_in_fs = sorted(cf_depts - fs_depts)
        extra_depts_in_fs = sorted(fs_depts - cf_depts)

        if missing_depts_in_fs:
            issues["missing_departments_in_field_subfield"].append({
                "college": college,
                "departments": missing_depts_in_fs
            })
        if extra_depts_in_fs:
            issues["extra_departments_in_field_subfield"].append({
                "college": college,
                "departments": extra_depts_in_fs
            })

        for dept in sorted(cf_depts | fs_depts):
            cf_fields = set(cf.get(college, {}).get(dept, [])) if isinstance(cf.get(college, {}).get(dept), list) else set()
            fs_fields = set(fs.get(college, {}).get(dept, {}).keys()) if isinstance(fs.get(college, {}).get(dept), dict) else set()

            missing_fields_in_fs = sorted(cf_fields - fs_fields)
            extra_fields_in_fs = sorted(fs_fields - cf_fields)

            if missing_fields_in_fs:
                issues["missing_fields_in_field_subfield"].append({
                    "college": college,
                    "department": dept,
                    "fields": missing_fields_in_fs
                })
            if extra_fields_in_fs:
                issues["extra_fields_in_field_subfield"].append({
                    "college": college,
                    "department": dept,
                    "fields": extra_fields_in_fs
                })

            for field in fs_fields:
                subfields = fs.get(college, {}).get(dept, {}).get(field)
                if not isinstance(subfields, list):
                    issues["invalid_subfield_type"].append({
                        "college": college, "department": dept, "field": field,
                        "detail": f"Expected list, got {type(subfields).__name__}"
                    })
                elif len(subfields) == 0:
                    issues["empty_subfields"].append({
                        "college": college, "department": dept, "field": field
                    })
                else:
                    seen = set()
                    dups = sorted([s for s in subfields if s in seen or seen.add(s)])
                    if dups:
                        issues["duplicate_subfields"].append({
                            "college": college, "department": dept, "field": field,
                            "duplicates": dups
                        })

    has_issues = any(len(v) > 0 for v in issues.values())
    if has_issues:
        print("\n=== DISCREPANCY REPORT ===")
        for key in sorted(issues.keys()):
            print(f"\n- {key}:")
            for item in issues[key]:
                print(f"  • {item}")
    else:
        print("No discrepancies found. ✅")

    if args.report_json:
        os.makedirs(os.path.dirname(args.report_json), exist_ok=True)
        with open(args.report_json, "w", encoding="utf-8") as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
        print(f"\nReport written to: {args.report_json}")

    if args.fail_on_issues and has_issues:
        sys.exit(2)


if __name__ == "__main__":
    main()
