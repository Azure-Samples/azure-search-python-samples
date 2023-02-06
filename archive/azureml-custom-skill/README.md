# Archived - Custom skill example using Azure Machine Learning and Azure Cognitive Search

![MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

This example is archived and no longer supported. The text of this readme is for the original sample and is out of date.

## Original introduction

In this sample, you will use the [hotel reviews dataset](https://www.kaggle.com/datafiniti/hotel-reviews) (distributed under [the Creative Commons license CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)) to create a custom skill using Azure Machine Learning to extract aspect-based sentiment from the reviews. This allows for the assignment of positive and negative sentiment within the same review to be correctly ascribed to identified entities like staff, room, lobby, or pool.

To train the aspect-based sentiment model, you will be using the [nlp recipes repository](https://github.com/microsoft/nlp-recipes/tree/master/examples/sentiment_analysis/absa). The model will then be deployed as an endpoint on an Azure Kubernetes cluster. Once deployed, the model is added to the enrichment pipeline as a custom skill for use by the Cognitive Search service.

There are two datasets provided. If you wish to train the model yourself, the `hotel_reviews_1000.csv` file is required. Prefer to skip the training step? Download the `hotel_reviews_100.csv`.

In this sample, skillset output is sent to a [knowledge store](https://docs.microsoft.com/azure/search/knowledge-store-concept-intro) in Azure Storage. Because knowledge store is not yet supported in the [**azure-search-documents**](https://docs.microsoft.com/python/api/overview/azure/search-documents-readme) python library, the [Search REST APIs](https://docs.microsoft.com/rest/api/searchservice/) are used instead.

## Contents

| File/folder | Description |
|-------------|-------------|
| `custom_skill_azureml.ipynb` | Jupyter notebook |
| `datasets` | Small and large datasets for use in this process |
| `model` | lexicon files for defining entities and opinions |
| `CONTRIBUTING.md` | Guidelines for contributing to the sample. |
| `LICENSE.md`   | The license for the sample. |
| `README.md` | This README file. |

## Prerequisites

* Azure subscription - get a [free subscription](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
* [Cognitive Search service](https://docs.microsoft.com/azure/search/search-get-started-arm)
* [Cognitive Services resource](https://docs.microsoft.com/azure/cognitive-services/cognitive-services-apis-create-account?tabs=multiservice%2Cwindows)
* [Azure Storage account](https://docs.microsoft.com/azure/storage/common/storage-account-create?toc=%2Fazure%2Fstorage%2Fblobs%2Ftoc.json&tabs=azure-portal)
* [Azure Machine Learning workspace](https://docs.microsoft.com/azure/machine-learning/how-to-manage-workspace)

## Setup

* Clone or download the contents of this repository.
* Extract contents if the download is a zip file. Make sure the files are read-write.
* While setting up the Azure accounts and services, copy the names and keys to an easily accessed text file. The names and keys will be added to the first cell in the notebook where variables for accessing the Azure services are defined.
* If you are unfamiliar with Azure Machine Learning and its requirements, you will want to review these documents before getting started:

* [Configure a development environment for Azure Machine Learning](https://docs.microsoft.com/azure/machine-learning/how-to-configure-environment)
* [Create and manage Azure Machine Learning workspaces in the Azure portal](https://docs.microsoft.com/azure/machine-learning/how-to-manage-workspace)
* When configuring the development environment for Azure Machine Learning, consider using the [cloud-based compute instance](https://docs.microsoft.com/azure/machine-learning/how-to-configure-environment#compute-instance) for speed and ease in getting started.

* Upload the dataset file to a container in the storage account. The [larger file](datasets\hotel_reviews_1000.csv) is necessary if you wish to perform the training step in the notebook. If you prefer to skip the training step, the [smaller file](datasets\hotel_reviews_100.csv) is recommended.

### Running the tutorial

* The notebook in this sample is detailed in the tutorial [Build and deploy a custom skill with Azure Machine Learning](https://docs.microsoft.com/azure/search/cognitive-search-tutorial-aml-custom-skill).
* Open the Jupyter notebook and enter all of the subscription, account names, and keys required in the first cell of the notebook. This will allow the notebook to access the Azure based services and perform the processes in each cell of the notebook.
* Once you have completed the exercise in the notebook, delete your resource group to avoid additional costs.

## Next steps

You can learn more about Azure Cognitive Search on the [official documentation site](https://docs.microsoft.com/azure/search/).
