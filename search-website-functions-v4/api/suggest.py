import logging
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from shared_code import azure_config
import json

environment_vars = azure_config()

# curl --header "Content-Type: application/json" \
#  --request POST \
#  --data '{"q":"code","top":"5", "suggester":"sg"}' \
#  http://localhost:7071/api/Suggest

# Set Azure Search endpoint and key
service_name = environment_vars["search_service_name"]
endpoint = f"https://{service_name}.search.windows.net"
key = environment_vars["search_api_key"]

# # Your index name
# index_name = "good-books"

# # Create Azure SDK client
# search_client = SearchClient(endpoint, index_name, AzureKeyCredential(key))


# bp=func.Blueprint()
# @bp.function_name("suggest")
# @bp.route(route="suggest", methods=[func.HttpMethod.GET, func.HttpMethod.POST] )
# def main(req: func.HttpRequest) -> func.HttpResponse:

#     # variables sent in body
#     req_body = req.get_json()
#     q = req_body.get("q")
#     top = req_body.get("top") or 5
#     suggester = req_body.get("suggester") or "sg"

#     if q:
#         logging.info("/Suggest q = %s", q)
#         suggestions = search_client.suggest(search_text=q, suggester_name=suggester, top=top)

#         # format the React app expects
#         full_response = {}
#         full_response["suggestions"] = suggestions
#         logging.debug(suggestions)

#         return func.HttpResponse(
#             body=json.dumps(full_response), mimetype="application/json", status_code=200
#         )
#     else:
#         return func.HttpResponse("No query param found.", status_code=200)
# Your index name
index_name = "partselect"

# Create Azure SDK client
search_client = SearchClient(endpoint, index_name, AzureKeyCredential(key))


bp=func.Blueprint()
@bp.function_name("suggest")
@bp.route(route="suggest", methods=[func.HttpMethod.GET, func.HttpMethod.POST] )
def main(req: func.HttpRequest) -> func.HttpResponse:

    # variables sent in body
    req_body = req.get_json()
    q = req_body.get("q")
    top = req_body.get("top") or 5
    suggester = req_body.get("suggester") or "sg"

    if q:
        logging.info("/Suggest q = %s", q)
        suggestions = search_client.suggest(search_text=q, suggester_name="modelsuggest", top=top,search_fields=["PartNum"] )
        
        # format the React app expects
        full_response = {}
        full_response["suggestions"] = suggestions
        logging.debug(suggestions)

        return func.HttpResponse(
            body=json.dumps(full_response), mimetype="application/json", status_code=200
        )
    else:
        return func.HttpResponse("No query param found.", status_code=200)