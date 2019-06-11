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

This repository contains Python sample code used in Azure Search quickstarts, tutorials, and examples.

## Quickstart-Jupyter-Notebook

This sample is a .ipynb file containing a Python3 notebook used in [Quickstart: Create and query an Azure Search index using a Jupyter Python notebook](https://docs.microsoft.com/azure/search/search-get-started-python). There are two placeholder values for an Azure Search service and admin API key. Replace them with valid values to create, load, and query an index on your own service.

## Tutorial-AI-Enrichment-Jupyter-Notebook

This sample is a .ipynb file containing a Python3 notebook used in [Tutorial: Python Tutorial: Call Cognitive Services APIs in an Azure Search indexing pipeline](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-blob-python). There are three placeholder values to insert: an Azure Search service, an admin API key, and a connection string to a blob storage resource that you will create in the tutorial. Replace them with valid values to create an indexing pipeline that searches for and extracts text and text representations of images and scanned documents. This sample leverages cognitive skills from the Azure Cognitive Services API, such as entity recognition and language detection.

Run the steps individually and make sure the printed response status or response output appears before continuing to the next step. The step that creates the indexer, in particular, may take a few minutes to complete.
