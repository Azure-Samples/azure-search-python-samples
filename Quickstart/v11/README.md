---
page_type: sample
languages:
  - python
name: Quickstart in Python
products:
  - azure
  - azure-cognitive-search
description: |
  Learn how to create, load, and query an Azure AI Search index using Python.
urlFragment: python-quickstart
---

# Python quickstart for Azure AI Search

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

Demonstrates using Python and the Azure SDK for Python to create an Azure AI Search index, load it with documents, and execute a few queries. The index is modeled on a subset of the Hotels dataset, reduced for readability and comprehension. Index definition and documents are included in the code.

This sample is a Jupyter Python3 .ipynb file to perform the actions against the Azure AI Search service.

## Prerequisites

* Visual Studio Code with the Python extension (or equivalent tool), with Python 3.7 or later

* [azure-search-documents package](https://pypi.org/project/azure-search-documents/) from the Azure SDK for Python

## Set up the sample

1. Clone or download this sample repository.

1. Extract contents if the download is a zip file. Make sure the files are read-write.

## Run the sample

1. Open the azure-search-quickstart.ipynb file in Visual Studio Code.

1. Open an integrated terminal and run `pip install azure-search-documents`.

1. Set the service endpoint and API key for your search service:

   * service_name = "YOUR-SEARCH-SERVICE-NAME"
   * admin_key = "YOUR-SEARCH-SERVICE-ADMIN-API-KEY"

1. Run each step in sequence.

## Next steps

You can learn more about Azure AI Search on the [official documentation site](https://docs.microsoft.com/azure/search).
