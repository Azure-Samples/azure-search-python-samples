# Python samples for Azure AI Search

This repository contains Python code samples used in Azure AI Search documentation. Unless noted otherwise, all samples run on the shared (free) pricing tier of an [Azure AI Search service](https://learn.microsoft.com/azure/search/search-create-service-portal).

| Sample | Description |
|--------|-------------|
| quickstart | "Day One" introduction to the fundamental tasks of working with a search index: create, load, and query. This sample is a Jupyter Python3 .ipynb file. The index is modeled on a subset of the Hotels dataset, widely used in Azure AI Search samples, but reduced here for readability and comprehension. |
| quickstart-semantic-search | Extends the quickstart through modifications that invoke semantic search. This notebook adds a semantic configuration to the index and semantic query options that formulate the query and response. |
<!-- | tutorial-ai-enrichment | This sample is a Jupyter Python3 .ipynb file used in the [Python Tutorial: Call Azure AI Services APIs in an Azure AI Search indexing pipeline](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-blob-python). This sample demonstrates Azure AI functionality, adding AI enrichments from Azure AI services to extract, detect, and analyze information from image files or large unstructured document files. | -->
| search-website-functions-v4 | Shows how to create, load, and query a search index in Python using the Azure.Search.Documents library in the Azure SDK for Python. It also includes application code and sample data so that you can see search integration in the context of a full app. The data is from [https://github.com/zygmuntz/goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k). The app is an Azure Static Web app, using the React library for user interaction, and Azure Function to handle the query requests and responses in the application layer. |

## Archived samples

+ **azureml-custom-skill**: See the **Archive** branch of this repository.
+ **image-processing**: See [azure-search-sample-archive/tree/main/image-processing](https://github.com/Azure-Samples/azure-search-sample-archive/tree/main/image-processing).
