"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS - Research Theme
File: createCollegeFieldMappings.py
Description: Splits MasterCollegeFieldMapping.json into per-college files under:
             data/context/collegeFieldMappings/<CollegeName>.json

Master format:
  college -> department -> (EITHER)
      - dict[field_name -> field_description (str)]
      - department_description (str)    # when there are no fields listed

Output format (per-college file):
  department -> (EITHER)
      - dict[field_name -> field_description (str)]
      - department_description (str)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from config.paths import (
        COLLEGE_FIELD_MAPPINGS_DIR,
        MASTER_COLLEGE_FIELD_MAPPING_JSON,
    )
except Exception as e:
    print(
        "ERROR: Could not import from config.paths. "
        "Ensure you run from project root or use `python -m misc.createCollegeFieldMappings`.\n"
        f"Details: {e}"
    )
    sys.exit(1)


def sanitize_filename(name: str) -> str:
    """Allow alnum, space, (), &, , . - _ and collapse whitespace."""
    cleaned = re.sub(r"[^\w\s\-\(\)&,\.]", "_", name, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "unnamed"


def write_json(path, obj, overwrite=False):
    if os.path.exists(path) and not overwrite:
        print(f"SKIP (exists): {path}")
        return "skipped"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"WROTE: {path}")
    return "written"


def main():
    parser = argparse.ArgumentParser(
        description="Create per-college JSON files (with field descriptions) from master college-field mapping."
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without writing files."
    )
    args = parser.parse_args()

    master_path = MASTER_COLLEGE_FIELD_MAPPING_JSON
    out_dir = COLLEGE_FIELD_MAPPINGS_DIR

    if not os.path.isfile(master_path):
        print(f"ERROR: Master mapping not found: {master_path}")
        sys.exit(1)

    with open(master_path, "r", encoding="utf-8") as f:
        master = json.load(f)

    os.makedirs(out_dir, exist_ok=True)
    results = {"written": 0, "skipped": 0}

    # master: college -> department -> (dict[field -> desc] OR department_desc str)
    for college, dept_map in master.items():
        if not isinstance(dept_map, dict):
            print(f"WARNING: Skipping college with invalid structure: {college}")
            continue

        college_filename = f"{sanitize_filename(college)}.json"
        out_path = os.path.join(out_dir, college_filename)

        # For per-college file, we simply write that college's department map as-is
        # (so field descriptions or department-only descriptions are preserved).
        if args.dry_run:
            print(f"DRY RUN: Would write {out_path}")
            continue

        status = write_json(out_path, dept_map, overwrite=args.overwrite)
        if status in results:
            results[status] += 1

    if not args.dry_run:
        print(f"\nSummary: {results['written']} written, {results['skipped']} skipped")


if __name__ == "__main__":
    main()
