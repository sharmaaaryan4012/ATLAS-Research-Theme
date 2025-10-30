from pydantic import BaseModel, Field
from typing import List, Optional
import json

class GeneratorResponseFormat(BaseModel):
    fields: List[str] = Field(description="A list of fields that match the research description")

class ReflectorResponseFormat(BaseModel):
    is_correct: bool = Field(description="Whether the provided classification is correct.")
    fields_to_remove: None | List[str] = Field(description="A list of the fields in the provided classification that are incorrect, or None if they are all correct.")

generator_response_schema = GeneratorResponseFormat.model_json_schema()
generator_response_schema_json = json.dumps(generator_response_schema, indent=2)

reflector_response_schema = ReflectorResponseFormat.model_json_schema()
reflector_response_schema_json = json.dumps(reflector_response_schema, indent=2)

def get_generator_response_schema():
    return generator_response_schema_json

def get_reflector_response_schema():
    return reflector_response_schema_json