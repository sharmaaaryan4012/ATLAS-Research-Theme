from lg.state import State
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import re

api_key = ""

generator = llm = ChatGoogleGenerativeAI(
            model= "gemini-2.5-pro",
            temperature=1.0,
            max_retries=2,
            google_api_key=api_key,
        )

reflector = llm = ChatGoogleGenerativeAI(
            model= "gemini-2.5-pro",
            temperature=1.0,
            max_retries=2,
            google_api_key=api_key,
        )

#Generators
def field_generator_node(state:State) -> State:
  response = generator.invoke(state["messages"][-1]).content
  
  print("field class result: ", response)
  schema = r'\{[^{}]*"fields"[^{}]*\}'
  matches = re.findall(schema, response, re.DOTALL)
  if matches:
      json_str = matches[-1]
      classification = json.loads(json_str)
      # classification = {"fields": ["American History", "Global & Transnational History"]}
      state["classification_bundle"].fields.field_names = classification["fields"]
      return {"messages": state["messages"], "classification_bundle": state["classification_bundle"]}

def subfield_generator_node(state:State) -> State:
  response = generator.invoke(state["messages"]).content
  # response = {"fields": ["African American History"]}
  schema = r'\{[^{}]*"fields"[^{}]*\}'
  matches = re.findall(schema, response, re.DOTALL)
  if matches:
      json_str = matches[-1]
      classification = json.loads(json_str)
      state["classification_bundle"].subfields.subfield_names = classification["fields"]
      return {"messages": state["messages"], "classification_bundle": state["classification_bundle"]}
  #add some error handling here
  print("JSON SCHEME NOT IDENTIFIED")
  return {"messages": state["messages"], "classification_bundle": state["classification_bundle"]}

#Reflectors
def field_reflector_node(state:State) -> State:
  response = reflector.invoke(state["messages"]).content
  print("RESPONSE reflect is: ", response)
  # result = {"is_correct": True, "fields_to_remove": None}
  schema = r'\{[^{}]*"is_correct"[^{}]*"fields_to_remove"[^{}]*\}'
  matches = re.findall(schema, response, re.DOTALL)
  if matches:
      json_str = matches[-1]
      result = json.loads(json_str)
      print("field ref result: ", result)
      state["classification_bundle"].satisfied_fields = result["is_correct"]
      state["classification_bundle"].fields.fields_to_remove = result["fields_to_remove"]
      return {"messages": state["messages"], "classification_bundle": state["classification_bundle"]}
  print("JSON FORMAT BAD")

def subfield_reflector_node(state:State) -> State:
  response = reflector.invoke(state["messages"]).content
  # result = {"is_correct": True, "fields_to_remove": None}
  schema = r'\{[^{}]*"is_correct"[^{}]*"fields_to_remove"[^{}]*\}'

  match = re.search(schema, response, re.DOTALL)
  if match:
      json_str = match.group(0)
      result = json.loads(json_str)
      print("sub ref result: ", result)
      state["classification_bundle"].satisfied_subfields = result["is_correct"]
      state["classification_bundle"].subfields.subfields_to_remove = result["fields_to_remove"]
      return {"messages": state["messages"], "classification_bundle": state["classification_bundle"]}
  print("JSON FORMAT BAD")