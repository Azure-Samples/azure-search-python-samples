import sys
import json
import requests
import pandas as pd
import os
import time
import fnmatch
import PyPDF2
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex
from azure.search.documents.indexes.models import (
    ComplexField,
    CorsOptions,
    SearchIndex,
    ScoringProfile,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)

# Get the service name (short name) and admin API key from the environment
service_name = "wsl-cog-search-test-2"
key = "9GUM9vU7CjGgZxiPNuvyBIzPo1uOtAqdvrSQdDMZYEAzSeBz1hrb"
endpoint = "https://{}.search.windows.net/".format(service_name)

# Give your index a name
# You can also supply this at runtime in __main__
index_name = "cartas-coordinador"

# Search Index Schema definition
index_schema = "./cartas-coordinador-index.json"

# PDFs filepath
# Books catalog
pdfs_filepath = "E:\AI\PDFs\Colbun"
batch_size = 1000

# Instantiate a client
class CreateClient(object):
    def __init__(self, endpoint, key, index_name):
        self.endpoint = endpoint
        self.index_name = index_name
        self.key = key
        self.credentials = AzureKeyCredential(key)

    # Create a SearchClient
    # Use this to upload docs to the Index
    def create_search_client(self):
        return SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credentials,
        )

    # Create a SearchIndexClient
    # This is used to create, manage, and delete an index
    def create_admin_client(self):
        return SearchIndexClient(endpoint=endpoint, credential=self.credentials)


# Get Schema from File or URL
def get_schema_data(schema, url=False):
    if not url:
        with open(schema) as json_file:
            schema_data = json.load(json_file)
            return schema_data
    else:
        data_from_url = requests.get(schema)
        schema_data = json.loads(data_from_url.content)
        return schema_data


# Create Search Index from the schema
# If reading the schema from a URL, set url=True
def create_schema_from_json_and_upload(schema, index_name, admin_client, url=False):

    cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)
    scoring_profiles = []
    schema_data = get_schema_data(schema, url)

    index = SearchIndex(
        name=index_name,
        fields=schema_data["fields"],
        scoring_profiles=scoring_profiles,
        suggesters=schema_data["suggesters"],
        cors_options=cors_options,
    )

    try:
        upload_schema = admin_client.create_index(index)
        if upload_schema:
            print(f"Schema uploaded; Index created for {index_name}.")
        else:
            exit(0)
    except:
        print("Unexpected error:", sys.exc_info()[0])

def convert_pdfs_to_json(root_dir):
    data_list = []
    id_count = 1

    for dirpath, dirs, files in os.walk(root_dir):
        for filename in fnmatch.filter(files, '*.pdf'):
            pdf_file = os.path.join(dirpath, filename)

            with open(pdf_file, 'rb') as fileobj:
                pdf = PyPDF2.PdfReader(fileobj)
                text = ''
                for page in pdf.pages:
                    text += page.extract_text()

                info = pdf.metadata
                author = info.author
                created_date = info.creation_date
                created_date_str = created_date.strftime("%Y%m%d%H%M%S")
                mod_date = info.modification_date
                mod_date_str = mod_date.strftime("%Y%m%d%H%M%S")
                num_pages = len(pdf.pages)

                data = {
                    "id": id_count,
                    "filename": os.path.basename(pdf_file),
                    "author": author,
                    "created_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.strptime(created_date_str[2:-2], "%Y%m%d%H%M%S")),
                    "last_modified_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.strptime(mod_date_str[2:-2], "%Y%m%d%H%M%S")),
                    "number_of_pages": num_pages,
                    "content": text
                }

                data_list.append(data)
                id_count += 1

    return data_list

# Batch your uploads to Azure Search
def batch_upload_json_data_to_index(json_file, client):
    batch_array = []
    count = 0
    batch_counter = 0
    for i in json_file:
        count += 1
        batch_array.append(
            {
                "id": str(i["id"]),
                "filename": i["filename"],
                "author": i["author"],
                "created_date": i["created_date"],
                "last_modified_date": i["last_modified_date"],
                "number_of_pages": i["number_of_pages"],
                "content": i["content"]
            }
        )

        # In this sample, we limit batches to 1000 records.
        # When the counter hits a number divisible by 1000, the batch is sent.
        if count % batch_size == 0:
            client.upload_documents(documents=batch_array)
            batch_counter += 1
            print(f"Batch sent! - #{batch_counter}")
            batch_array = []

    # This will catch any records left over, when not divisible by 1000
    if len(batch_array) > 0:
        client.upload_documents(documents=batch_array)
        batch_counter += 1
        print(f"Final batch sent! - #{batch_counter}")

    print("Done!")


if __name__ == "__main__":
    start_client = CreateClient(endpoint, key, index_name)
    admin_client = start_client.create_admin_client()
    search_client = start_client.create_search_client()
    schema = create_schema_from_json_and_upload(
        index_schema, index_name, admin_client, url=False
    )
    pdfs_data = convert_pdfs_to_json(pdfs_filepath)
    batch_upload = batch_upload_json_data_to_index(pdfs_data, search_client)
    print("Upload complete")
