---
page_type: sample
languages:
  - python
name: Image processing in Python
products:
  - azure
  - azure-cognitive-search
description: |
  Skillsets in Cognitive Search can process images, making that content usable in other scenarios. This sample demonstrates an image file workflow, using OCR and redaction of personal information.
urlFragment: python-sample-image-processing
---

# Image Processing Sample

Cognitive Search can analyze images with text, or images with other images, to create searchable or analyzable text. This sample focuses on a specific aspect of image analysis in a Cognitive Search pipeline: passing images to a custom skill, and return images back to the skillset for further processing.

In this demonstration, you will use a sample JPEG file, services and tools, and fully formulated requests in notebook to perform the following tasks:

1. Crack a sample source JPG file from Blob storage and scrape the image for text, using the [Optical Character Recognition (OCR) skill](https://docs.microsoft.com/azure/search/cognitive-search-skill-ocr) in Cognitive Search.
1. Analyze the resulting text for personal information, such as phone numbers, using the [PII skill](https://docs.microsoft.com/azure/search/cognitive-search-skill-pii-detection).
1. Split the text into smaller units and blur the units that contain phone numbers. Use a [custom skill](https://docs.microsoft.com/azure/search/cognitive-search-custom-skill-web-api) for this task.
1. Reconstitute the image in Blob storage. Use the [TextMerge skill](https://docs.microsoft.com/azure/search/cognitive-search-skill-textmerger) for this step.

Post-OCR, the skillset runs the extracted text through the PII detection skill to identify personal information (phone numbers). The custom skill then obfuscates the phone numbers by accepting as inputs the image, the layout text from  OCR step, and the identified personal information. Output of the custom skill is the image with obfuscated sections. The output is then returned to the skillset and projected to the knowledge store.

The source input and resulting output are stored in Azure Blob storage, so you will need a storage account to complete this tutorial.

Predefined skills, such as OCR skill, are backed by Cognitive Services. You will need the Cognitive Services account name for this tutorial, but because the number of transformations is limited, there is no charge to your account.

Custom skills must be hosted as a URL-accessible module. This tutorial uses Azure Functions to satisfy this requirement, but you could use another mechanism for your own solutions.

## Prerequisites

+ [Azure subscription](https://Azure.Microsoft.com/subscription/free)
+ [Azure Cognitive Search service](https://docs.microsoft.com/azure/search/search-create-service-portal) (get the full service endpoint and an admin API key)
+ [Azure Blob storage service](https://docs.microsoft.com/azure/storage/common/storage-account-create) (get the connection string)
+ [Azure Cognitive Services](https://docs.microsoft.com/azure/cognitive-services/cognitive-services-apis-create-account) (get the account name)
+ [Python 3.6+](https://www.python.org/downloads/)
+ [Jupyter Notebook](https://jupyter.org/install)
+ [Visual Studio Code](https://code.visualstudio.com/download) with the [Azure Functions extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions) and the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

## Configure the components

Before you open the notebook, assemble the resources that are referenced by the skillset.

1. Download the **azure-search-python-samples** repository and extract its contents. 

1. Open the **image-processing** sample folder to find the files used in this sample.

### In Azure portal

1. Set up the data source. In Azure portal, in Azure Blob storage, create a container named "brf-sample", and then upload the sample JPEG file (microsoft.jpg) from the sample folder.

1. From **Keys**, copy the Azure Storage connection string and paste it into NotePad.

1. Navigate to your search service, copy the search endpoint (http://<SERVICE-NAME>.search.windows.net) and an admin API key.

1. Navigate to Cognitive Services, copy the account name. 

### In Visual Studio Code

1. Set up the function app that contains the custom code. In Visual Studio code, navigate to the **image-processing** sample folder.

1. Right-click the **SplitImage** folder and select **Deploy to Function App**. You will be prompted for a subscription, region, and other properties that are required to set up the app.

   ![Deploy as function](media/image-process-split-image-deploy-function-app.png)

1. Monitor notifications in the Output window (**View** > **Output**) for a "Deployment successful" message.

1. Still in Visual Studio Code, switch to **Azure: Function** explorer.

1. Open the subscription folder and find the app you just deployed.

1. Open the Functions folder, right-click **ImageSkill HTTP**, and then copy the function URL. Save it Notepad.

   ![Copy function URL](media/image-process-function-url.png)

## Run the Python code in the notebook

1. Open the BFR_Sample_Rest.ipynb file in Jupyter Notebook.

1. In the first cell, paste in the following information:

   * search service endpoint
   * search service admin API key
   * Azure Storage connection string
   * Cognitive Services account name
   * Blob container that contains the JPEG
   * Function app URL

1. Run each cell.

## Validation

Once the indexer completes, use the Azure portal and Storage explorer in your Azure Storage account to find the final output. You will see a container `obfuscated` in the knowledge store that contains the same image you started with, but with the phone number redacted. For comparison, the original image is stored in a container `images`.
