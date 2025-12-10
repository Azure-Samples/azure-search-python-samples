# Python samples for Azure AI Search

This repository contains Python code samples used in Azure AI Search documentation. Unless noted otherwise, all samples run on the shared (free) pricing tier of a [search service](https://learn.microsoft.com/azure/search/search-create-service-portal).

If your configuration uses a search service managed identity for indexer connections, your search service must be on the Basic tier or higher.

## Day-one quickstarts and tutorials

| Sample | Description |
|--------|-------------|
| [Quickstart](Quickstart/README.md) | Introduces the fundamental tasks of working with a classic search index: create, load, and query. The index is modeled on a subset of the hotels dataset, which is widely used in Azure AI Search samples but reduced in this sample for readability and comprehension. |
| [Quickstart-Agentic-Retrieval](Quickstart-Agentic-Retrieval/quickstart-agentic-retrieval.ipynb) | Create a knowledge base in Azure AI Search to integrate LLM reasoning into query planning. |
| [Quickstart-Document-Permissions-Pull-API](Quickstart-Document-Permissions-Pull-API/document-permissions-pull-api.ipynb) | Using an indexer "pull API" approach, flow access control lists from a data source to search results and apply permission filters that restrict access to authorized content. Indexer support is limited to Azure Data Lake Storage (ADLS) Gen2 permission metadata. |
| [Quickstart-Document-Permissions-Push-API](Quickstart-Document-Permissions-Push-API/document-permissions-push-api.ipynb) | Using the push APIs for indexing a JSON payload, flow embedded permission metadata to indexed documents and search results that are filtered based on user access to authorized content. |
| [Quickstart-RAG](Quickstart-RAG/quickstart-rag.ipynb) | Introduces LLM integration with a chat model, such as GPT-3.5-turbo or an equivalent model. |
| [Quickstart-Semantic-Search](Quickstart-Semantic-Search/semantic-search-quickstart.ipynb) | Extends the quickstart through modifications that invoke semantic ranking. This notebook adds a semantic configuration to the index and semantic query options that formulate the query and response. |
| [Quickstart-Vector-Search](Quickstart-Vector-Search/quickstart-vector-search.ipynb) | Introduces vector search in Azure AI Search. This notebook demonstrates how to create, load, and query a vector index. |

## Deeper dive tutorials

| Sample | Description |
|--------|-------------|
| [agentic-retrieval-pipeline-example](agentic-retrieval-pipeline-example/agent-example.ipynb) | Extends the quickstart by integrating Foundry Agent Service. Add an AI agent and MCP tool to your Azure AI Search agentic retrieval pipeline for an end-to-end conversational search experience. |
| [azure-function-search](azure-function-search/readme.md) | An Azure Function that sends query requests to an Azure AI Search service. You can substitute this code to replace the contents of the `api` folder in the C# sample [azure-search-static-web-app](https://github.com/Azure-Samples/azure-search-static-web-app). |
| [bulk-insert](bulk-insert/readme.md) | Create and load an index using the push APIs and sample data. You can substitute this code to replace the contents of the `bulk-insert` folder in the C# sample [azure-search-static-web-app](https://github.com/Azure-Samples/azure-search-static-web-app) |
| [cmk-encryption](cmk-example/cmk-example.ipynb) | Encrypt content using customer-managed keys. |

## Archived samples

+ **azureml-custom-skill**: See the **Archive** branch of this repository.
+ **image-processing**: See [azure-search-sample-archive/tree/main/image-processing](https://github.com/Azure-Samples/azure-search-sample-archive/tree/main/image-processing).
