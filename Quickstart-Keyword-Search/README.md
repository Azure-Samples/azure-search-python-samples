---
page_type: sample
languages:
  - python
name: Python keyword search quickstart for Azure AI Search
products:
  - azure
  - azure-cognitive-search
description: |
  Learn how to create, load, and query an Azure AI Search index using Python.
urlFragment: python-quickstart-keyword
---

# Python keyword search quickstart for Azure AI Search

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

This sample demonstrates how to use the Azure SDK for Python to create an Azure AI Search index, load it with documents, and execute queries. The index is modeled on a subset of the hotels dataset, which is reduced in this sample for readability and comprehension. The code includes the index definition and documents.

This sample uses a Jupyter notebook (.ipynb) file to perform the actions against the Azure AI Search service.

## Prerequisites

* [Visual Studio Code](https://code.visualstudio.com/download) with the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and [Jupyter package](https://pypi.org/project/jupyter/).

* The [azure-search-documents package](https://pypi.org/project/azure-search-documents/) from the Azure SDK for Python.

## Set up the sample

1. Clone or download this sample repository.

1. Extract contents if the download is a zip file. Make sure the files are read-write.

## Run the sample

1. Open the azure-search-quickstart.ipynb file in Visual Studio Code.

1. Set the service endpoint and API key for your search service:

   * service_name = "YOUR-SEARCH-SERVICE-NAME"
   * admin_key = "YOUR-SEARCH-SERVICE-ADMIN-API-KEY"

1. Run each step in sequence.

## Next step

You can learn more about Azure AI Search on the [official documentation site](https://learn.microsoft.com/azure/search).
