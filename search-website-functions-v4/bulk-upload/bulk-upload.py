import sys
import json
import requests
import pandas as pd
import os
import openai
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

# OpenAI API
openai.api_type = "azure"
openai.api_base = "https://wsl-openai-canada.openai.azure.com/"
openai.api_version = "2023-03-15-preview"
openai.api_key = "1c7f2e52b7a34bf783e1fd632e83613f"

# Prompts
SYSTEM_MESSAGE = """You are extracting information from a letter. The items you need to extract are: The date of the letter, Who is sending the letter, A short paragraph summary (in spanish) of the letter, and a sentiment analysis of the letter (positive, negative, neutral). You must reply in JSON format."""
INSRTUCTIONS = """[LETTER]Santiago, 16 de agosto de 2023
 DE03759-23
Señores
Encargados Titulares
Empresas Coordinadas
Presente
Ref.: Programa de Operación del 
Sistema Eléctrico Nacional 
correspondiente al día 17 de agosto
de 2023
De nuestra consideración:
Por medio de la presente, envío para su conocimiento el programa de operación
de la Ref., cuyos antecedentes y base de datos, que permiten reproducir los 
resultados obtenidos, se encuentran disponibles en el sitio web del Coordinador 
Eléctrico Nacional, información a la cual puede acceder a través de la siguiente 
ruta:
www.coordinador.cl ➔ Operación ➔ Documentos ➔ Programas de operación.
Los caudales afluentes utilizados en la programación se obtienen de acuerdo con 
lo indicado en el Decreto N°51-2021.
A partir de la programación de la operación del 04 de julio del 2023, el proceso de 
programación de mediano plazo considera 28 series hidrológicas sintéticas 
basadas en el estado actual de las cuencas y la estadística meteorológica de los 
últimos 28 años.
Sin otro particular, saluda atentamente a usted,
 Juan Marcos Donoso N.
Jefe Depto. de Programación
Coordinador Eléctrico Nacional
[ANSWER]{
"sender": "Juan Marcos Donoso N., Jefe Depto. de Programación, Coordinador Eléctrico Nacional",
"date": "16 de agosto de 2023",
"summary": "Por medio de esta carta, Juan Marcos Donoso N., Jefe del Departamento de Programación del Coordinador Eléctrico Nacional, informa a las empresas coordinadas sobre el programa de operación del Sistema Eléctrico Nacional correspondiente al día 17 de agosto de 2023. Además, indica que los antecedentes y la base de datos necesarios para reproducir los resultados obtenidos están disponibles en la página web del Coordinador Eléctrico Nacional. Menciona que a partir de la programación de la operación del 4 de julio de 2023, se consideran 28 series hidrológicas sintéticas.",
"sentiment": "neutral"
}"""

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
        
        
def llm_extract(text):
    messages = []
    messages.append({"role":"system", "content": SYSTEM_MESSAGE})
    messages.append({"role":"user", "content": f"{INSRTUCTIONS}\n[LETTER]{text}\n[ANSWER]"})
    response = openai.ChatCompletion.create(engine="gpt-35-turbo-16k", messages = messages, temperature=0.7)
    json_info = None
    try:
        json_info = json.loads(response["choices"][0]["message"]["content"])
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    return json_info

def llm_transform_date(text):
    messages = []
    messages.append({"role":"system", "content": "Transform this date to Edm.DateTimeOffset format"})
    messages.append({"role":"user", "content": f"{text}"})
    response = openai.ChatCompletion.create(engine="gpt-35-turbo", messages = messages, temperature=0.7)
    result = response["choices"][0]["message"]["content"]
    return result

def extract_info_from_pdf(pdf_file, id):
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
        
        if num_pages > 2:
            return None

        data = {
            "id": id,
            "filename": os.path.basename(pdf_file),
            "author": author,
            "created_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.strptime(created_date_str[2:-2], "%Y%m%d%H%M%S")),
            "last_modified_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.strptime(mod_date_str[2:-2], "%Y%m%d%H%M%S")),
            "number_of_pages": num_pages,
            "content": text
        }
        
        # extract and add the llm info
        llm_info = llm_extract(text)
        data["sender"] = llm_info["sender"]
        data["date"] = llm_transform_date(llm_info["date"])
        data["summary"] = llm_info["summary"]
        data["sentiment"] = llm_info["sentiment"]

        print(data)
        return data

def convert_pdfs_to_json(root_dir):
    data_list = []
    id_count = 1
    
    for dirpath, dirs, files in os.walk(root_dir):
        for filename in fnmatch.filter(files, '*.pdf'):
            pdf_file = os.path.join(dirpath, filename)
            data = extract_info_from_pdf(pdf_file, id_count)
            if data is not None: 
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
                "content": i["content"],
                "sender": i["sender"],
                "date": i["date"],
                "summary": i["summary"],
                "sentiment": i["sentiment"]
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
