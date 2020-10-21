---
page_type: sample
languages:
  - python
name: Quickstart in Python - Jupyter Notebook
products:
  - azure
  - azure-cognitive-search
description: |
  Learn how to create, load, and query an Azure Cognitive Search index using Python and the latest-version REST APIs
urlFragment: python-sample-quickstart
---

# Quickstart sample for Azure Cognitive Search using Python

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

Demonstrates using Python and the Azure SDK for Python to create an Azure Cognitive Search index, load it with documents, and execute a few queries. The index is modeled on a subset of the Hotels dataset, reduced for readability and comprehension. Index definition and documents are included in the code.

This sample is a Jupyter Python3 .ipynb file to perform the actions against the Cognitive Search service.

## Contents

| File/folder | Description |
|-------------|-------------|
| `azure-search-quickstart.ipynb`       | Jupyter Python notebook. |
| `.gitignore` | Define what to ignore at commit time. |
| `CONTRIBUTING.md` | Guidelines for contributing to the sample. |
| `README.md` | This README file. |
| `LICENSE`   | The license for the sample. |

## Prerequisites

- [Anaconda 3.x](https://www.anaconda.com/distribution/#download-section) providing Python 3.x and Jupyter Notebooks
- [Azure Cognitive Search service](https://docs.microsoft.com/azure/search/search-create-service-portal)
- Azure Cognitive Search SDK for Python (pip install azure-search-documents --pre)

## Setup

1. Clone or download this sample repository.
2. Extract contents if the download is a zip file. Make sure the files are read-write.

## Running the sample
1. On the Windows Start menu, select Anaconda3, and then select Jupyter Notebook.
1. Open the azure-search-quickstart.ipynb file in Jupyter Notebook
1. Replace <service_name> <admin_key> and <query_key> with the service and api-key details of your search service
1. Run each step individually

## Next steps

You can learn more about Azure Cognitive Search on the [official documentation site](https://docs.microsoft.com/azure/search).
