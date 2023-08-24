import json
import logging

import azure.functions as func
import openai
from shared_code import azure_config
from Search import azure_search
from .prompts import SYSTEM_MESSAGE, DECOMPOSE_INSTRUCTIONS, EXAMPLES_DECOMPOSE, FINAL_ANSWER_INSTRUCTIONS

FUNCTIONS = [
    {
      "name": "Search",
      "description": "Search the Azure index of 'cartas-coordinador' and return results based on the query",
      "parameters": {
        "type": "object",
        "properties": {
          "q": {
            "type": "string",
            "description": "The search query"
          }
        },
        "required": ["q"]
      }
    }
]

environment_vars = azure_config()

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Input must be a JSON object", status_code=400
        )

    messages = req_body.get('messages')
    query = req_body.get('query')
    if not query:
        return func.HttpResponse(
            "No query found in input JSON", status_code=400
        )
        
    # OpenAI API Setup
    openai.api_type = "azure"
    openai.api_base = environment_vars["azure_openai_endpoint"]
    openai.api_version = environment_vars["azure_openai_api_version"]
    openai.api_key = environment_vars["azure_openai_key"]
    
    # Create Prompt
    prompt = []
    for message in messages:
        prompt.append(message)
    prompt.append({"role":"user", "content":query})
    response = openai.ChatCompletion.create(
        engine="gpt-35-turbo", 
        messages=prompt, 
        temperature=0.7
        )
    
    logging.info(response)    
    
    return func.HttpResponse(
        body=json.dumps(response), mimetype="application/json", status_code=200
    )