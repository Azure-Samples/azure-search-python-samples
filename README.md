# Python samples for Azure AI Search

This repository contains Python code samples used in Azure AI Search documentation. Unless noted otherwise, all samples run on the shared (free) pricing tier of an [Azure AI Search service](https://learn.microsoft.com/azure/search/search-create-service-portal).

| Sample | Description |
|--------|-------------|
| [azure-function-search](azure-function-search/readme.md) | This sample is an Azure Function that sends query requests to an Azure AI Search service. You can substitute this code to replace the contents of the `api` folder in the C# sample [azure-search-static-web-app](https://github.com/Azure-Samples/azure-search-static-web-app). |
| [bulk-insert](bulk-insert/readme.md) | This sample shows you how to create and load an index using the push APIs and sample data. You can substitute this code to replace the contents of the `bulk-insert` folder in the C# sample [azure-search-static-web-app](https://github.com/Azure-Samples/azure-search-static-web-app) |
| cmk-encryption | This example shows you how to encrypt content using customer-managed keys.|
| quickstart | "Day One" introduction to the fundamental tasks of working with a search index: create, load, and query. This sample is a notebook .ipynb file. The index is modeled on a subset of the Hotels dataset, widely used in Azure AI Search samples, but reduced here for readability and comprehension. |
| quickstart-semantic-search | Extends the quickstart through modifications that invoke semantic search. This notebook adds a semantic configuration to the index and semantic query options that formulate the query and response. |
| quickstart-rag | "Day One" introduction to LLM integration with a chat model such as GPT-3.5-turbo or equivalent. |
| tutorial-rag | A deeper dive into LLM integration with a chat model such as GPT-3.5-turbo or equivalent. |

## Archived samples

+ **azureml-custom-skill**: See the **Archive** branch of this repository.
+ **image-processing**: See [azure-search-sample-archive/tree/main/image-processing](https://github.com/Azure-Samples/azure-search-sample-archive/tree/main/image-processing).
