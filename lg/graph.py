from typing import Literal
import sys
from config import paths
sys.path.append(paths.PROJECT_ROOT)

from lg.state import State
from lg.tools import generator_prompt, reflector_prompt
from lg.agents import field_generator_node, field_reflector_node, subfield_generator_node, subfield_reflector_node
from langgraph.graph import StateGraph
from models.request import UserRequest
from models.classification import ClassificationBundle


graph = StateGraph(State)

def print_classification(state:State, location):
    classification_bundle = state["classification_bundle"]
    fields = classification_bundle.fields
    satisfied_fields = classification_bundle.satisfied_fields
    subfields = classification_bundle.subfields
    satisfied_subfields = classification_bundle.satisfied_subfields
    print("At ", location)
    print("Fields: ", fields.field_names)
    print("Satisfied with Fields: ", satisfied_fields)
    print("Subfields: ", subfields.subfield_names)
    print("Satisfied with Subfields: ", satisfied_subfields)

#Connect request and field_classifier
def field_classifier(state: State):
    print_classification(state, "field classifier")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields_classification = classification_bundle.fields
    fields_to_remove = fields_classification.fields_to_remove #after reflection
    prompt = generator_prompt(research_description = research_description,
                               department = department, 
                               remove = fields_to_remove)
    return {"messages": [prompt]}


#Connect field_classifier and field validator
def field_validator(state: State):
    print_classification(state, "field validator")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields_classification = classification_bundle.fields
    classification = fields_classification.field_names
    fields_to_remove = fields_classification.fields_to_remove

    prompt = reflector_prompt(research_description = research_description,
                                department = department,
                                classification = classification,
                                remove = fields_to_remove)
    return {"messages": [prompt]}

#Conditional Node for field: Good or bad? Repeat.

def field_conditional_edge(state: State) -> Literal['field_classifier', 'subfield_classifier']:
    classification_bundle = state["classification_bundle"]
    needs_revision = not classification_bundle.satisfied_fields
    if needs_revision:
        print("FIELD: needs revision")
        return "field_classifier"
    else:
        return "subfield_classifier"

#Connect to field updater

def subfield_classifier(state: State):
    print_classification(state, "subfield classifier")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department
    classification_bundle = state["classification_bundle"]
    fields = classification_bundle.fields.field_names
    subfields_classification = classification_bundle.subfields
    subfields_to_remove = subfields_classification.subfields_to_remove
    prompt = generator_prompt(research_description = research_description,
                                department = department,
                                fields = fields,
                                remove = subfields_to_remove)
    return {"messages": [prompt]}

def subfield_validator(state: State):
    print_classification(state, "subfield validator")
    user_request = state["user_request"]
    research_description = user_request.research_description
    department = user_request.department

    classification_bundle = state["classification_bundle"]
    fields = classification_bundle.fields.field_names
    subfields_classification = classification_bundle.subfields
    classification = subfields_classification.subfield_names
    subfields_to_remove = subfields_classification.subfields_to_remove

    prompt = reflector_prompt(research_description = research_description,
                                department = department,
                                classification = classification,
                                fields = fields,
                                remove = subfields_to_remove)
    return {"messages": [prompt]}

#Conditional Node for subfield: Good or bad? Repeat.
def subfield_conditional_edge(state: State) -> Literal['subfield_classifier', '__end__']:
    classification_bundle = state["classification_bundle"]
    needs_revision = not classification_bundle.satisfied_fields
    if needs_revision:
        print("SUBFIELD: needs revision")
        return "subfield_classifier"
    else:
        return "__end__"

#add nodes
graph.add_node("field_classifier", field_classifier)
graph.add_node("field_validator", field_validator)
graph.add_node("subfield_classifier", subfield_classifier)
graph.add_node("subfield_validator", subfield_validator)
#add agents
graph.add_node("field_generator_node", field_generator_node)
graph.add_node("field_reflector_node", field_reflector_node)
graph.add_node("subfield_generator_node", subfield_generator_node)
graph.add_node("subfield_reflector_node", subfield_reflector_node)

#set entry point
graph.set_entry_point("field_classifier")

#add edges

#fields
graph.add_edge("field_classifier", "field_generator_node")
graph.add_edge("field_generator_node", "field_validator")
graph.add_edge("field_validator", "field_reflector_node")

graph.add_conditional_edges("field_reflector_node", field_conditional_edge)

#subfields
graph.add_edge("subfield_classifier", "subfield_generator_node")
graph.add_edge("subfield_generator_node", "subfield_validator")
graph.add_edge("subfield_validator", "subfield_reflector_node")

graph.add_conditional_edges("subfield_reflector_node", subfield_conditional_edge)

APP = graph.compile()

#input into the graph - this information will be provided by the user
faculty_description = """US imperialism; race's relationship to gender and sexuality; climate

My research takes transimperial, interimperial, and international approaches. In my first book I examined the intersections of settler colonialism and Black removal efforts (e.g. Liberian colonization), illuminating the centrality of languages of climate, race, and gender to intellectual debates over geographies of Black freedom.

My other works include peer-reviewed articles on the U.S. opening of Japan and how it generated imaginings of difference and affinity that unsettled the Black-white dichotomy and the binarized correspondence of gender and sexuality dominating popular discourse in the U.S. East. 

I am currently working on a book manuscript on U.S. imperialism in the Pacific up to the end of the Philippine-American War.  """

department = "History"

#build the initial state
user_request = UserRequest()
user_request.research_description = faculty_description
user_request.department = department

start_state: State = {
    "messages": [],
    "user_request": user_request,
    "classification_bundle": ClassificationBundle()
}

print(start_state["user_request"])

final_state = APP.invoke(start_state)

print_classification(final_state, "END RESULTS")