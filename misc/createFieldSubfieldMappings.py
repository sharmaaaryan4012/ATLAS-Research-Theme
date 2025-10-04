"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS - Research Theme
File: createFieldSubfieldMappings.py
Description: Splits MasterFieldSubfieldMapping.json into per-field files under:
             data/context/FieldSubfieldMappings/<FieldName>.json
             Each file contains a list of subfields for that Field.
             If a field name appears in multiple colleges/departments with different lists,
             files will be disambiguated by appending a slug of the college/department.
"""

from pathlib import Path
import json
import os
import sys
import argparse
import re
from hashlib import md5

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from config.paths import (
        MASTER_FIELD_SUBFIELD_MAPPING_JSON,
        FIELD_SUBFIELD_MAPPINGS_DIR,
    )
except Exception as e:
    print(
        "ERROR: Could not import from config.paths. "
        "Ensure you run from project root or use `python -m misc.createFieldSubfieldMappings`.\n"
        f"Details: {e}"
    )
    sys.exit(1)


def sanitize_filename(name: str) -> str:
    """Allow alnum, space, (), &, , . - _ and collapse whitespace."""
    cleaned = re.sub(r"[^\w\s\-\(\)&,\.]", "_", name, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "unnamed"


def slugify(s: str) -> str:
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^\w\-]", "", s)
    return s[:60] or "x"


def _content_hash(obj) -> str:
    return md5(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def safe_write_field_json(
    field_name: str,
    subfields,
    base_dir: str,
    context_suffix: str,
    overwrite: bool,
    dry_run: bool,
):
    """
    Write <FieldName>.json if unique or same content; otherwise write <FieldName>-<context_suffix>.json.
    """
    filename = f"{sanitize_filename(field_name)}.json"
    path = os.path.join(base_dir, filename)

    desired_hash = _content_hash(subfields)

    # Primary target exists?
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if _content_hash(existing) == desired_hash:
                print(f"SKIP (same content): {path}")
                return "skipped"
            else:
                # Disambiguate
                alt_name = f"{sanitize_filename(field_name)}-{context_suffix}.json"
                alt_path = os.path.join(base_dir, alt_name)
                if dry_run:
                    print(f"DRY RUN: Would write (collision) {alt_path}")
                    return "skipped"
                with open(alt_path, "w", encoding="utf-8") as f:
                    json.dump(subfields, f, indent=2, ensure_ascii=False)
                print(f"WROTE (collision): {alt_path}")
                return "written"
        except Exception:
            if not overwrite:
                alt_name = f"{sanitize_filename(field_name)}-{context_suffix}.json"
                alt_path = os.path.join(base_dir, alt_name)
                if dry_run:
                    print(f"DRY RUN: Would write (existing unreadable) {alt_path}")
                    return "skipped"
                with open(alt_path, "w", encoding="utf-8") as f:
                    json.dump(subfields, f, indent=2, ensure_ascii=False)
                print(f"WROTE (existing unreadable, disambiguated): {alt_path}")
                return "written"

    # Normal path
    if dry_run:
        print(f"DRY RUN: Would write {path}")
        return "skipped"

    if os.path.exists(path) and overwrite:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(subfields, f, indent=2, ensure_ascii=False)
        print(f"WROTE (overwrote): {path}")
        return "written"

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(subfields, f, indent=2, ensure_ascii=False)
        print(f"WROTE: {path}")
        return "written"

    print(f"SKIP (exists, use --overwrite to replace): {path}")
    return "skipped"


def main():
    parser = argparse.ArgumentParser(
        description="Create per-field JSON mappings from master field-subfield mapping."
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files when names collide with different content.")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files.")
    args = parser.parse_args()

    master_path = MASTER_FIELD_SUBFIELD_MAPPING_JSON
    out_dir = FIELD_SUBFIELD_MAPPINGS_DIR

    if not os.path.isfile(master_path):
        print(f"ERROR: Master mapping not found: {master_path}")
        sys.exit(1)

    with open(master_path, "r", encoding="utf-8") as f:
        master = json.load(f)

    os.makedirs(out_dir, exist_ok=True)
    results = {"written": 0, "skipped": 0}

    # Traverse: college -> department -> field -> [subfields]
    for college, dept_map in master.items():
        if not isinstance(dept_map, dict):
            print(f"WARNING: Skipping college with invalid structure: {college}")
            continue
        for dept, field_map in dept_map.items():
            if not isinstance(field_map, dict):
                print(f"WARNING: Skipping dept with invalid structure: {college} / {dept}")
                continue
            for field, subfields in field_map.items():
                if not isinstance(subfields, list):
                    print(f"WARNING: Subfields not a list, skipping: {college} / {dept} / {field}")
                    continue

                ctx_suffix = f"{slugify(college)}_{slugify(dept)}"
                status = safe_write_field_json(
                    field_name=field,
                    subfields=subfields,
                    base_dir=out_dir,
                    context_suffix=ctx_suffix,
                    overwrite=args.overwrite,
                    dry_run=args.dry_run,
                )
                if status in results:
                    results[status] += 1

    if not args.dry_run:
        print(f"\nSummary: {results['written']} written, {results['skipped']} skipped")


if __name__ == "__main__":
    main()
