---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-cognitive-search
name: AI enrichment tutorial - Jupyter Notebook
description: |
  Create an AI enrichment pipeline in Azure Cognitive Search to extract text, structure, and information from raw content, including images and unstructured text.
urlFragment: python-tutorial-cognitive-search
---

# Get started with skillsets and AI enrichment in Azure Cognitive Search

Demonstrates AI enrichment by building an indexing pipeline that detects and extracts text and text representations of images and scanned documents stored as blobs in Azure Blob storage. This sample leverages cognitive skills from the Cognitive Services APIs, such as entity recognition and language detection. It uses the REST APIs to make calls to Azure Cognitive Search, including index definition, data ingestion and AI enrichment, and query execution.

This sample is a Jupyter Python3 .ipynb file used in [Python Tutorial: Call Cognitive Services APIs in an enrichment pipeline](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-blob-python). 

## Contents

| File/folder | Description |
|-------------|-------------|
| `PythonTutorial-AzureSearch-AIEnrichment.ipynb`       | Jupyter Python notebook. |
| `.gitignore` | Define what to ignore at commit time. |
| `CONTRIBUTING.md` | Guidelines for contributing to the sample. |
| `README.md` | This README file. |
| `LICENSE`   | The license for the sample. |

## Prerequisites

- [Anaconda 3.x](https://www.anaconda.com/distribution/#download-section) providing Python 3.x and Jupyter Notebooks
- [Sample file set (mixed content types)](https://github.com/Azure-Samples/azure-search-sample-data/tree/master/mixedContent)
- [Azure Storage account](https://docs.microsoft.com/azure/storage/common/storage-quickstart-create-account) 
- [Azure Cognitive Search service](https://docs.microsoft.com/en-us/azure/search/search-create-service-portal)

## Setup

1. Clone or download this sample repository.
2. Extract contents if the download is a zip file. Make sure the files are read-write.

## Running the sample
1. On the Windows Start menu, select Anaconda3, and then select Jupyter Notebook.
2. Open the PythonTutorial-AzureSearch-AIEnrichment.ipynb file in Jupyter Notebook.
3. Replace <YOUR-SERVICE-NAME> and <YOUR-ADMIN-API-KEY> with the service and api-key details of your search service.
4. Replace <YOUR-BLOB-RESOURCE-CONNECTION-STRING> with a connection string to an Azure Blob storage resource that you created, and to which you uploaded [content files](https://github.com/Azure-Samples/azure-search-sample-data/tree/master/mixedContent) of various file types.
5. Run each step individually.

By sequentially executing each step, you can verify the printed response status or response output appears before continuing to the next step. The step that creates the indexer, in particular, may take a few minutes to complete. See the tutorial for more details.