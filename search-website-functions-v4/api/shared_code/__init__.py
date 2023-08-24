import os


def azure_config():

    configs = {}
    configs["search_facets"] = os.environ.get("SearchFacets", "")
    configs["search_index_name"] = os.environ.get("SearchIndexName", "")
    configs["search_service_name"] = os.environ.get("SearchServiceName", "")
    configs["search_api_key"] = os.environ.get("SearchApiKey", "")
    configs["azure_openai_endpoint"] = os.environ.get("AzureOpenaiEndpoint", "")
    configs["azure_openai_api_version"] = os.environ.get("AzureOpenaiApiVersion", "")
    configs["azure_openai_key"] = os.environ.get("AzureOpenaiKey", "")

    return configs
