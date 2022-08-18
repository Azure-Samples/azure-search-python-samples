# Python sample repository for Azure Cognitive Search

This repository contains Python sample code used in Azure Cognitive Search quickstarts, tutorials, and examples. You can use the shared (free) Azure Cognitive Search service to run any sample in this repository.

## All steps sample - Create an Azure Search Index with Cognitive Search from scratch

This sample provides all steps to create a new Azure Search Index with Cognitive Search and load it with the provided sample data from scratch. The idea is that no prior knowledge about Azure Search is required. This sample consists of two Jupiter Notebooks and accompanying materials. 

## Quickstart sample - Azure Cognitive Search

This sample is a Jupyter Python3 .ipynb file used in [Quickstart: Create and query a search index using a Jupyter Python notebook](https://docs.microsoft.com/azure/search/search-get-started-python). Learn how to use the [**azure-search-documents**](https://docs.microsoft.com/python/api/overview/azure/search-documents-readme) client library in the Azure SDK for Python to make service connections, create and load indexes, and run basic queries.

## Tutorial sample - Add search to a web app

This sample shows how to create, load, and query a search index in Python using the Azure.Search.Documents library in the Azure SDK for Python. It also includes application code and sample data so that you can see search integration in the context of a full app. The data is from [https://github.com/zygmuntz/goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k). The app is an Azure Static Web app, using the React library for user interaction, and Azure Function to handle the query requests and responses in the application layer.

## Tutorial sample - Add a skillset (enrichments) to an indexing pipeline

This sample is a Jupyter Python3 .ipynb file used in the [Python Tutorial: Call Cognitive Services APIs in an Azure Cognitive Search indexing pipeline](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-blob-python). This sample demonstrates cognitive search functionality, adding AI enrichments from Cognitive Services to extract, detect, and analyze information from image files or large unstructured document files.

## Tutorial sample - Image processing

This sample is a Jupyter Python3 .ipynb file that shows how to work with image skills in a skillset. Although the skillset performs useful operations, including Optical Character Recognition (OCR) and redaction of personally identifying information, the sample's purpose is to demonstrate the coordination of image file handoffs from one skill to the next.

In this sample, skillset output is sent to a [knowledge store](https://docs.microsoft.com/azure/search/knowledge-store-concept-intro) in Azure Storage. Because knowledge store is not yet supported in the [**azure-search-documents**](https://docs.microsoft.com/python/api/overview/azure/search-documents-readme) python library, the [Search REST APIs](https://docs.microsoft.com/rest/api/searchservice/) are used instead.

## Tutorial sample - Train and deploy a custom skill with Azure Machine Learning

This sample is a Jupyter Python3 .ipynb file. It's used in the [Tutorial: Build and deploy a custom skill with Azure Machine Learning](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-aml-custom-skill). This sample provides an end-to-end walk through for training and deploying an aspect-based sentiment model to an Azure Kubernetes cluster for consumption as a custom skill in a Cognitive Search enrichment pipeline. Azure Machine Learning is used to train and deploy the model.

In this sample, skillset output is sent to a [knowledge store](https://docs.microsoft.com/azure/search/knowledge-store-concept-intro) in Azure Storage. Because knowledge store is not yet supported in the [**azure-search-documents**](https://docs.microsoft.com/python/api/overview/azure/search-documents-readme) python library, the [Search REST APIs](https://docs.microsoft.com/rest/api/searchservice/) are used instead.