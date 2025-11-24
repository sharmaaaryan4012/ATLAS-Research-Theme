import os

from dotenv import load_dotenv

from langgraph.graph import BuildGraph
from langgraph.models import UserRequest
from llm.llm_adapter import GeminiJSONAdapter

dotenv_path = "config/api.env"
load_dotenv(dotenv_path=dotenv_path)
api_key = os.getenv("LANGSMITH_KEY")
if api_key:
    os.environ["LANGSMITH_KEY"] = api_key
else:
    print("Warning: LANGSMITH_KEY not found in config/api.env")

os.environ["LANGSMITH_TRACING_V2"] = "true"
os.environ["LANGSMITH_PROJECT"] = "Research-Theme-Project"

llm = GeminiJSONAdapter.from_env(model_name="gemini-2.5-flash")

graph = BuildGraph(
    unit_classifier_llm=llm,
    unit_validator_llm=llm,
    field_classifier_llm=llm,
    field_validator_llm=llm,
    field_enhancer_llm=llm,
    field_enhancement_validator_llm=llm,
    subfield_classifier_llm=llm,
    subfield_validator_llm=llm,
)

req = UserRequest(
    request_id="test-1",
    description=(
        """
Monte Carlo theory and methodology, and their applications to scientific problems
Statistical inference on network data
State space models and dynamic systems
Bioinformatics and population genetics


        """
    ),
    college_name="College of Liberal Arts & Sciences"
)

print("Running graph...")
state = graph.Run(req)
print("Graph run complete. Check your LangSmith dashboard.")

print("Chosen units:", state.get_units())
print(
    "Units valid? ",
    state.unit_validation.is_valid if state.unit_validation else None,
)

print("Chosen programs:", state.get_fields())
print(
    "Programs valid? ",
    state.field_validation.is_valid if state.field_validation else None,
)
print("Chosen subfields:", state.get_subfields())
print(
    "Subfields valid? ",
    state.subfield_validation.is_valid if state.subfield_validation else None,
)
print("New Suggested Fields?:", state.get_new_fields())
