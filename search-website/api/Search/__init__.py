import logging
import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from shared_code import azure_config
import json

environment_vars = azure_config()

# Set Azure Search endpoint and key
endpoint = f'https://{environment_vars["search_service_name"]}.search.windows.net'
key = environment_vars["search_api_key"]

# Your index name
index_name = 'good-books'

# Create Azure SDK client
search_client = SearchClient(endpoint, index_name, AzureKeyCredential(key))

# returns obj like {authors: 'array', language_code:'string'}
def read_facets(facetsString):
    facets = facetsString.split(",")
    output = {}
    for x in facets:
        if(x.find('*') != -1):
            newVal = x.replace('*','')
            output[newVal]='array'
        else: 
            output[x]='string'
    return output


# creates filters in odata syntax
def create_filter_expression(filter_list, facets):
    i = 0
    filter_expressions = []
    return_string = ""
    separator = ' and '

    while (i < len(filter_list)) :
        field = filter_list[i]["field"]
        value = filter_list[i]["value"]

        if (facets[field] == 'array'): 
            print('array')
            filter_expressions.append(f'{field}/any(t: search.in(t, \'{value}\', \',\'))')
        else :
            print('value')
            filter_expressions.append(f'${field} eq \'{value}\'');
        
        i += 1
    

    return separator.join(filter_expressions)

def new_shape(docs):
    
    old_api_shape = list(docs)
    
    count=0
    client_side_expected_shape = []
    
    for item in old_api_shape:
        
        new_document = {}
        new_document["score"]=item["@search.score"]
        new_document["highlights"]=item["@search.highlights"]

        new_shape = {}
        new_shape["id"]=item["id"]
        new_shape["goodreads_book_id"]=item["goodreads_book_id"]
        new_shape["best_book_id"]=item["best_book_id"]
        new_shape["work_id"]=item["work_id"]        
        new_shape["books_count"]=item["books_count"]        
        new_shape["isbn"]=item["isbn"]
        new_shape["isbn13"]=item["isbn13"]
        new_shape["authors"]=item["authors"]
        new_shape["original_publication_year"]=item["original_publication_year"]
        new_shape["original_title"]=item["original_title"]
        new_shape["title"]=item["title"]
        new_shape["language_code"]=item["language_code"]
        new_shape["average_rating"]=item["average_rating"]
        new_shape["ratings_count"]=item["ratings_count"]
        new_shape["work_ratings_count"]=item["work_ratings_count"]
        new_shape["work_text_reviews_count"]=item["work_text_reviews_count"]
        new_shape["ratings_1"]=item["ratings_1"]
        new_shape["ratings_2"]=item["ratings_2"]
        new_shape["ratings_3"]=item["ratings_3"]
        new_shape["ratings_4"]=item["ratings_4"]
        new_shape["ratings_5"]=item["ratings_5"]
        new_shape["image_url"]=item["image_url"]
        new_shape["small_image_url"]=item["small_image_url"]
        
        new_document["document"]=new_shape
        
        client_side_expected_shape.append(new_document)
    
    return list(client_side_expected_shape)

def main(req: func.HttpRequest) -> func.HttpResponse:

    # variables sent in body
    req_body = req.get_json()
    q = req_body.get('q')
    top = req_body.get('top') or 8
    skip = req_body.get('skip') or 0
    filters = req_body.get('filters') or []

    facets = environment_vars["search_facets"]
    facetKeys = read_facets(facets)
    filter= create_filter_expression(filters, facets)

    if q:
        logging.info(f"/Search q = {q}")
        
        search_results = search_client.search(search_text=q, top=top,skip=skip, facets=facetKeys, filter=filter, include_total_count=True)
        
        returned_docs = new_shape(search_results)
        returned_count = search_results.get_count()
        returned_facets = search_results.get_facets()
        
        # format the React app expects
        full_response = {}
        
        full_response["count"]=search_results.get_count()
        full_response["facets"]=search_results.get_facets()
        full_response["results"]=returned_docs
        
        
        return func.HttpResponse(body=json.dumps(full_response), mimetype="application/json",status_code=200)
    else:
        return func.HttpResponse(
             "No query param found.",
             status_code=200
        )

