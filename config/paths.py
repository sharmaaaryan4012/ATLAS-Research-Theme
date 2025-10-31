"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS - Research Theme
File: paths.py
Description: Centralized path management for the project.
"""

import os

# Root of the project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# === TOP-LEVEL DIRS ===
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
LANGGRAPH_DIR = os.path.join(PROJECT_ROOT, "lg")
MISC_DIR = os.path.join(PROJECT_ROOT, "misc")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
NOTEBOOKS_DIR = os.path.join(PROJECT_ROOT, "notebooks")
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

# === DATA SUBDIRS ===
DATA_CONTEXT_DIR = os.path.join(DATA_DIR, "context")
COLLEGE_FIELD_MAPPINGS_DIR = os.path.join(DATA_CONTEXT_DIR, "collegeFieldMappings")
FIELD_SUBFIELD_MAPPINGS_DIR = os.path.join(DATA_CONTEXT_DIR, "FieldSubfieldMappings")

JSONS_DIR = os.path.join(DATA_DIR, "jsons")
PARAMETERS_DIR = os.path.join(JSONS_DIR, "parameters")
SERIALIZATION_DIR = os.path.join(JSONS_DIR, "serialization")

KNOWLEDGEBASE_DIR = os.path.join(DATA_DIR, "knowledgebase")

# === MASTER JSON FILES ===
MASTER_COLLEGE_FIELD_MAPPING_JSON = os.path.join(
    DATA_CONTEXT_DIR, "MasterCollegeFieldMapping.json"
)
MASTER_FIELD_SUBFIELD_MAPPING_JSON = os.path.join(
    DATA_CONTEXT_DIR, "MasterFieldSubfieldMapping.json"
)

# === DOCS SUBDIRS ===
DIAGRAMS_DIR = os.path.join(DOCS_DIR, "diagrams")

# === SRC SUBDIRS ===
SRC_AGENTS_DIR = os.path.join(SRC_DIR, "agents")
SRC_CONFIG_DIR = os.path.join(SRC_DIR, "config")
SRC_CONTEXT_DIR = os.path.join(SRC_DIR, "context")

# === MISC SCRIPTS ===
CREATE_COLLEGE_FIELD_MAPPINGS_SCRIPT = os.path.join(
    MISC_DIR, "createCollegeFieldMappings.py"
)
CREATE_FIELD_SUBFIELD_MAPPINGS_SCRIPT = os.path.join(
    MISC_DIR, "createFieldSubfieldMappings.py"
)
CHECK_MAPPING_DISCREPANCY_SCRIPT = os.path.join(MISC_DIR, "checkMappingDiscrepency.py")
