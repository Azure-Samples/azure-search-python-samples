import logging
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex

# Get the service endpoint and API key from the environment
endpoint = 'https://YOUR-SEARCH-RESOURCE-NAME.search.windows.net'
key = 'YOUR-SEARCH-ADMIN-KEY'

# Your index name
index_name = 'good-books'

# Create Azure SDK client
search_client = SearchClient(endpoint, index_name, AzureKeyCredential(key))

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    docid = req.params.get('id')
    if not docid:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            docid = req_body.get('id')

    if docid:
        returnedDocument = search_client.get_document(key=docid)
        return func.HttpResponse(body=f"{returnedDocument}", status_code=200)
    else:
        return func.HttpResponse(
             "No doc id param found.",
             status_code=200
        )
