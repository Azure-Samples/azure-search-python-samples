---
page_type: sample
languages:
  - python
  - rest
name: Azure Cognitive Search Quickstart in Python
products:
  - azure
  - cognitive-search
description: |
  Learn basic steps for creating, loading, and querying a search index using REST APIs and a Jupyter Python3 notebook.
urlFragment: python-sample-quickstart
---

# Quickstart sample for Azure Cognitive Search using Python

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

Demonstrates connecting to Azure Cognitive Search, creating and loading an index consisting of fictitious hotel data, and running queries. A Jupyter Python Notebook is used to run this code. Calls to Azure Cognitive Search are through the REST APIs.

This sample is a Jupyter Python3 .ipynb file used in [Quickstart: Create and query a search index using a Jupyter Python notebook](https://docs.microsoft.com/azure/search/search-get-started-python)

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

## Setup

1. Clone or download this sample repository.
2. Extract contents if the download is a zip file. Make sure the files are read-write.

## Running the sample
1. On the Windows Start menu, select Anaconda3, and then select Jupyter Notebook.
1. Open the azure-search-quickstart.ipynb file in Jupyter Notebook
1. Replace <YOUR-SERVICE-NAME> and <YOUR-ADMIN-API-KEY> with the service and api-key details of your search service
1. Run each step individually

## Next steps

You can learn more about Azure Cognitive Search on the [official documentation site](https://docs.microsoft.com/azure/search).
