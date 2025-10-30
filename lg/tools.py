
from typing import List, Optional
from models.llm_output import get_generator_response_schema, get_reflector_response_schema
from data.context import collegeFieldMappings
import json

#Format the generator queries. Take a the list of descriptions + description
def generator_prompt(research_description: str, department: str, fields: Optional[List[str]] = None, remove: Optional[List[str]] = None):
    """formats the LLM Prompt for generating either fields or subfields

    Input:
    research_description: professor's research
    deparment: department input by user
    fields: if we have moved onto subfield classfication, draw from these fields.
    remove: options to remove from list

    Output:
    formatted LLM prompt
    """

    field_data = field_updater(department, fields, remove)

    background_text = f"You are an expert research domain classifier. Your goal is to determine which academic fields best match a {department} faculty member’s research description."

    introduce_fields = f'''Below is a list of academic fields, each paired with a short description. Use these definitions to guide your classification.

    {field_data}

                        '''
    introduce_description = f'''Faculty research description:

    \"{research_description}\"

                            '''
    
    format_instructions = f'''Your response should be a JSON object conforming to the following schema:

    ```json
    {get_generator_response_schema()}

                        '''

    query= f'''{background_text} 
    {introduce_fields}
    {introduce_description}
    {format_instructions}'''

    print("QUERY: ", query) 
    return query


#Format the reflector queries. Take a the list of descriptions + description + previous query
def reflector_prompt(research_description: str, department: str, classification: List[str], fields: Optional[List[str]] = None, remove: Optional[List[str]] = None):
    """formats the LLM Prompt for generating either fields or subfields

    Input:
    research_description: professor's research
    deparment: department input by user
    fields: if we have moved onto subfield classfication, draw from these fields.
    remove: options to remove from list

    Output:
    formatted LLM prompt
    """

    field_data = field_updater(department, fields, remove)

    background_text = f"You are a precise evaluator that checks whether a {department} faculty research description has been correctly classified into research fields by another evaluator. Your goal is to verify if the classifier’s choices align with the provided field definitions."

    introduce_fields = f'''Below is a list of academic fields, each paired with a short description. Use these definitions to evaluate correctness.

    {field_data}

    '''
    introduce_description = f'''Faculty research description:

    \"{research_description}\"

                            '''
    previous_classification = f'''Previous evaluator classification: 
                        
    {classification}
                        
                        '''
    task_instructions = '''Your Task
1. Review the generator’s proposed list of fields.
2. Decide whether each field is justified by the research description and the field definitions above.
3. If a field is clearly not supported by the description, mark it for removal.
4. Do not add new fields — only verify or remove incorrect ones.
5. Base all decisions strictly on the field definitions provided.
                        '''
    
    format_instructions = f'''Your response should be a JSON object conforming to the following schema:

    ```json
    {get_reflector_response_schema()}

                            '''

    query= f'''{background_text} 
    {introduce_fields}
    {introduce_description}
    {previous_classification}
    {task_instructions}
    {format_instructions}'''
    
    print("QUERY: ", query)
    return query
#Field updater here

def field_updater(department: str, fields: Optional[List[str]] = None, remove: List[str] = [], add: List[str] = None):
    if fields is None:
        path = f"data/context/collegeFieldMappings/College of Liberal Arts & Sciences.json"

        with open(path, 'r') as file:
            department_descriptions = json.load(file)
            fields_data = department_descriptions[department]
            if remove is not None:
                for field_to_remove in remove:
                    if field_to_remove in fields_data:
                        del fields_data[field_to_remove]
            return fields_data
        
    else:
        subfield_descriptions = {}
        for field in fields:
            path = f"data/context/FieldSubfieldMappings/{field}.json"
            with open(path, 'r') as file:
                subfields = json.load(file)
                if remove is not None:
                    for field_to_remove in remove:
                        if field_to_remove in subfields:
                            del subfields[field_to_remove]
                subfield_descriptions = subfield_descriptions | subfields
        return subfield_descriptions
                


        
    