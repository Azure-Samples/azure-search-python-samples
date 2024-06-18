from dotenv import load_dotenv
import os
from tqdm import tqdm
import requests
import json

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
)
from azure.search.documents import SearchClient

load_dotenv()

class AzureAISrch():
    def __init__(self) -> None:
        load_dotenv(override=True) # take environment variables from .env.
        
        # Azure Search Service Naming
        self.search_service_naming = os.environ["AZURE_SEARCH_SERVICE_NAMING"]
        self.search_index_name ="index-fsmone-sg"
        self.search_endpoint = "https://{}.search.windows.net/".format(self.search_service_naming)
        self.search_credential = AzureKeyCredential(os.environ["AZURE_SEARCH_ADMIN_KEY"]) if len(os.environ["AZURE_SEARCH_ADMIN_KEY"]) > 0 else DefaultAzureCredential()
 
    def create_or_update_search_index(self, schema):
        index_client = SearchIndexClient(endpoint=self.search_endpoint, credential=self.search_credential)
        fields = schema["fields"]
        cors_options = schema["corsOptions"]  
        scoring_profiles = schema["scoringProfiles"]
        suggesters = schema["suggesters"]

        # Create the search index
        index = SearchIndex(
            name=self.search_index_name, 
            fields=fields, 
            scoring_profiles=scoring_profiles,
            cors_options=cors_options,
            suggesters=suggesters
        )

        result = index_client.create_or_update_index(index)  
        print(f"(SEARCH INDEX) - CREATED or UPDATED -search index- {result.name}")  


    def indexing_files_by_batch(self, file):
        search_client = SearchClient(endpoint=self.search_endpoint, credential=self.search_credential, index_name=self.search_index_name)
        i = 0
        batch = []
        for i, dict in tqdm(enumerate(file), total=len(file)):
            batch.append(dict)
            if (i+1) % 1000 == 0:
                search_client.merge_or_upload_documents(documents=batch)
                print(f"Done upserting {i+1} files")
                batch = []

        if len(batch) > 0:
            search_client.merge_or_upload_documents(documents=batch)
            print(f"Done upserting {i+1} files")


def get_json_data(path_json, url=False):
    if not url:
        with open(path_json, "r") as f:
            json_data = json.load(f)
            return json_data
    else:
        resp = requests.get(path_json)
        json_data = resp.json()
        return json_data

def main():
    path_schema = "./data/schema-fsmoneSG.json"
    path_product = "./data/product-fsmoneSG.json"

    data_schema = get_json_data(path_schema)
    data_product = get_json_data(path_product)

    # Configure the Azure Search Index
    search = AzureAISrch()
    search.create_or_update_search_index(data_schema)
    search.indexing_files_by_batch(data_product)

if __name__ == "__main__":
    main()