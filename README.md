# Python samples for Azure AI Search

This repository contains Python code samples used in Azure AI Search documentation. Unless noted otherwise, all samples run on the shared (free) pricing tier of an [Azure AI Search service](https://learn.microsoft.com/azure/search/search-create-service-portal). If your configuration uses a search service managed identity for indexer connections, or if the samples uses semantic ranker, your search service must be basic tier or higher.

## Day-one quickstarts and tutorials

| Sample | Description |
|--------|-------------|
| [Quickstart](Quickstart/README.md) | "Day One" introduction to the fundamental tasks of working with a classic search index: create, load, and query. This sample is a Jupyter notebook (.ipynb) file. The index is modeled on a subset of the Hotels dataset, widely used in Azure AI Search samples, but reduced here for readability and comprehension. |
| [Quickstart-Semantic-Search](Quickstart-Semantic-Search/semantic-search-quickstart.ipynb) | Extends the quickstart through modifications that invoke semantic ranking. This notebook adds a semantic configuration to the index and semantic query options that formulate the query and response. You must have basic tier or higher for this quickstart.|
| [Quickstart-RAG](Quickstart-RAG/quickstart-rag.ipynb) | "Day One" introduction to LLM integration with a chat model such as GPT-3.5-turbo or equivalent. We recommend the basic tier or higher for this quickstart.|
| [Quickstart-Document-Permissions-Pull-API](Quickstart-Document-Permissions-Pull-API/document-permissions-pull-api.ipynb) | Using an indexer "pull API" approach, flow access control lists from a data source to search results and apply permission filters that restrict access to authorized content. Indexer support is limited to Azure Data Lake Storage (ADLS) Gen2 permission metadata. You must have  basic tier or higher for this quickstart.|
| [Quickstart-Document-Permissions-Push-API](Quickstart-Document-Permissions-Push-API/document-permissions-push-api.ipynb) | Using the push APIs for indexing a JSON payload, flow embedded permission metadata to indexed documents, and to search results that are filtered based on user access to authorized content. We recommend the basic tier or higher for this quickstart.|
| [Quickstart-Agentic-Retrieval](Quickstart-Agentic-Retrieval/quickstart-agentic-retrieval.ipynb) | Set up a search agent in Azure AI Search to integrate LLM reasoning into query planning. We recommend the basic tier or higher for this quickstart. |
|[Tutorial-RAG](Tutorial-RAG/tutorial-rag.ipynb) | A deeper dive into LLM integration with a chat model such as GPT-3.5-turbo or equivalent. We recommend the basic tier or higher for this quickstart. |

## Deeper dive tutorials

| Sample | Description |
|--------|-------------|
| [agentic-retrieval-pipeline-example](agentic-retrieval-pipeline-example/agent-example.ipynb) | This sample demonstrates integration with Azure AI Agent service, adding an AI agent and tool for an end-to-end conversational search experience. |
| [azure-function-search](azure-function-search/readme.md) | This sample is an Azure Function that sends query requests to an Azure AI Search service. You can substitute this code to replace the contents of the `api` folder in the C# sample [azure-search-static-web-app](https://github.com/Azure-Samples/azure-search-static-web-app). |
| [bulk-insert](bulk-insert/readme.md) | This sample shows you how to create and load an index using the push APIs and sample data. You can substitute this code to replace the contents of the `bulk-insert` folder in the C# sample [azure-search-static-web-app](https://github.com/Azure-Samples/azure-search-static-web-app) |
| [cmk-encryption](cmk-example/cmk-example.ipynb) | This example shows you how to encrypt content using customer-managed keys.|

## Archived samples

+ **azureml-custom-skill**: See the **Archive** branch of this repository.
+ **image-processing**: See [azure-search-sample-archive/tree/main/image-processing](https://github.com/Azure-Samples/azure-search-sample-archive/tree/main/image-processing).
