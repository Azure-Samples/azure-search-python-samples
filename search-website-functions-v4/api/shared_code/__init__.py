import os


def azure_config():

    configs = {}
    configs["search_facets"] = "authors*,language_code"
    configs["search_index_name"] = "good-books"
    configs["search_service_name"] = "aisrch-poc-uscentral-01"
    configs["search_api_key"] = "XE8nyqGGhtVXqmSlsrJPW0yEMiHocP7dWwktdCSclpAzSeATbtHu"

    return configs
