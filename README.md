---
topic: sample
services: azure-search
languages:
  - python
name: Azure Search Sample Data
description: |
  Find Python samples for Azure Search in this repo.
products:
  - azure-search
---
# Azure Search Python Samples repository

This repository contains Python sample code used in Azure Search quickstarts, tutorials, and examples. You can use the shared (free) Azure Search service to run any sample in this repository.

## Quickstart

This sample is a Jupyter Python3 .ipynb file used in [Quickstart: Create and query an Azure Search index using a Jupyter Python notebook](https://docs.microsoft.com/azure/search/search-get-started-python). 

### Running the quickstart
+ Open the azure-search-quickstart.ipynb file in Jupyter Notebook
+ Replace <YOUR-SERVICE-NAME> and <YOUR-ADMIN-KEY> with the service and api-key details of your Azure Search service
+ Run each step individually

## Tutorial-AI-Enrichment-Jupyter-Notebook

This sample is a Jupyter Python3 .ipynb file used in [Python Tutorial: Call Cognitive Services APIs in an Azure Search indexing pipeline](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-blob-python). 

This sample creates an Azure Search indexing pipeline that searches for and extracts text and text representations of images and scanned documents stored as blobs in Azure Blob storage. This sample leverages cognitive skills from the Azure Cognitive Services API, such as entity recognition and language detection.

### Running the tutorial
+ Open the PythonTutorial-AzureSearch-AIEnrichment.ipynb file in Jupyter Notebook
+ Replace <YOUR-SERVICE-NAME> and <YOUR-ADMIN-KEY> with the service and api-key details of your Azure Search service
+ Replace <YOUR-BLOB-RESOURCE-CONNECTION-STRING> with a connection string to an Azure Blob storage resource that you created, and to which you uploaded [content files](https://github.com/Azure-Samples/azure-search-sample-data/tree/master/mixedContent) of various file types.
+ Run each step individually

By sequentially executing each step, you can verify the printed response status or response output appears before continuing to the next step. The step that creates the indexer, in particular, may take a few minutes to complete. See the tutorial for more details.



