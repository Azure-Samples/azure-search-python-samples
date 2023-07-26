---
page_type: sample
languages:
  - python
name: Add search to a Python app
products:
  - azure
  - azure-cognitive-search
  - azure-static-web-app
description: |
  Add document search to a web app. This Python sample uses the Azure.Search.Documents library to create, load, and query the index.
urlFragment: python-sample-search-web-app
---

# Add search to a web app in Python

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

This Python sample shows you how to add document search to a web app using Azure Cognitive Search.

For this sample, you will use the [**azure-search-documents**](https://pypi.org/project/azure-search-documents/) library in the Azure SDK for Python to create, load, and query a search index containing the goodbooks-10k dataset, publicly available at [https://github.com/zygmuntz/goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k). The search index runs on an [Azure Cognitive Search](https://docs.microsoft.com/azure/search/search-what-is-azure-search) service that you create. You can use the free tier for this sample.

Optionally, this sample includes a devcontainer.json file so that you can run the code locally, as a developer, with the assurance that the environment is correctly configured and your local system doesn't need anything beyond docker. You'll need the [Docker extension](https://code.visualstudio.com/docs/containers/overview) to do this. If you don't want to us Docker, you can run your code in a virtual environment instead. 

The application itself is deployed as an Azure Static web app (which you can run locally), using the JavaScript React library to build the user interface and Azure Functions to handle the query requests against the search index.

This README is an shortened version of the [full Python tutorial](https://docs.microsoft.com//azure/search/tutorial-python-overview). 

Related resources:

* [Demo](https://victorious-beach-0ab88b51e.azurestaticapps.net/)

* [Conceptual documentation](https://docs.microsoft.com/azure/search/)

* [API reference](https://docs.microsoft.com/python/api/overview/azure/search-documents-readme?view=azure-python)

* New to Python in Visual Studio Code? See [Getting Started with Python in Visual Studio Code](https://code.visualstudio.com/docs/python/python-tutorial)

Below is a screenshot of the app created through this sample code.

![Screenshot of sample web app](./docs/images/web-app.png)

You can deploy the sample onto Azure or run it locally by following the steps below.

## Prerequisites

* [Python 3.7 or later](https://www.python.org/downloads/)
* [Visual Studio Code](https://code.visualstudio.com/Download)
* [Visual Studio  Code extension: Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
* [Visual Studio  Code extension: Azure Functions](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions&WT.mc_id=shopathome-github-jopapa)
* [Visual Studio Code extension: Azure Static Web Apps](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurestaticwebapps)
* [Azure Cognitive Search](https://docs.microsoft.com/azure/search/search-create-service-portal)

[Visual Studio Code extension: Docker](https://code.visualstudio.com/docs/containers/overview) is optional, but necessary if you want to run the Python code in a container.

Azure Static Web Apps is also required but you do not need to have this resource in advance. These instructions include inline steps for creating and configuring the web app in a later section.

## Setup

1. Clone (or Fork and Clone) this repository.
1. Open `./search-website` in Visual Studio Code.

This sample code runs the Azure Function API remotely on your cloned repository. If you intend to run it locally, you need to [install azure-functions-core-tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local?WT.mc_id=shopathome-github-jopapa) globally with the following bash command: `npm install -g azure-functions-core-tools@3 --unsafe-perm true`

## Create and load the index

1. In Visual Studio Code, create a virtual environment.

   * Ctrl+Shift+P > Terminal: Create New Integrated Terminal
   * At the PS terminal command line, run these commands:

     * `py -3 -m venv .venv`
     * `.venv\scripts\activate`

   You should see `(.venv)` in the PS command prompt. For example, `(.venv) PS C:\Users\user-name\azure-search-python-samples\search-website>`

1. Run bulk-upload.py to load data.

   * Change the following values in the `bulk_upload.py` file:

     * Search service name (short name)
     * Admin API key ([find the key in the portal](https://docs.microsoft.com/azure/search/search-security-api-keys#find-existing-keys))

   * Set the Python interpreter to your virtual environment. Ctrl+Shift+P > Python: Select Interpreter, choosing your .venv environment. Refresh the list if you don't see a .venv option.

   * Install Python libraries and load the data. At the PS command line:

     * `cd \bulk-upload`  
     * `py -m pip install -r requirements.txt`
     * `py bulk-upload.py`

   You should see status messages when the script runs, and you should have a good-books index created on your search service.

## Deploy the web app

Deploy the search-enabled website as an Azure Static web app. This deployment includes both the React app and the Function app for the user interface and business layer, respectively.

The following instructions create and configure the Azure Static Web App resource.

1. Select **Azure** from the Activity Bar, then select **Static Web Apps** from the Side bar.

1. Right-click on the subscription name then select **Create Static Web App (Advanced)**.

1. Follow the prompts to provide the following information:

    |Prompt|Enter|
    |--|--|
    |How do you want to create a Static Web App?|Use existing GitHub repository|
    |Choose organization|Select your _own_ GitHub alias as the organization.|
    |Choose repository|Select **azure-search-python-samples** from the list. |
    |Choose branch of repository|Select **main** from the list. |
    |Enter the name for the new Static Web App.|Create a unique name for your resource. For example, you can prepend your name to the repository name such as, `joansmith-azure-search-python-samples`. |
    |Select a resource group for new resources.|Use the resource group you created for this tutorial.|
    |Choose build preset to configure default project structure.|Select **Custom**|
    |Select the location of your application code|`search-website/client`|
    |Enter the path of your build output...|build|
    |Select a location for new resources.|Select a region close to you.|

1. The resource is created, select **Open Actions in GitHub** from the Notifications. This opens a browser window pointed to your forked repo. 

    The list of actions indicates your web app, both client and functions, were successfully pushed to your Azure Static Web App. 

    Wait until the build and deployment complete before continuing. This may take a minute or two to finish.

1. Select **Azure** from the Activity Bar. 

1. Right-click on your Static web app resource then select **Open in Portal**.

1. Select **Configuration** then select **+ Add**.

1. Add each of the following settings:

    |Setting|Your Search resource value|
    |--|--|
    |SearchApiKey|Your Search query key. You can [find query keys in the Azure portal](https://docs.microsoft.com/azure/search/search-security-api-keys#find-existing-keys)|
    |SearchServiceName|Your Search resource name|
    |SearchIndexName|`good-books`|
    |SearchFacets|`authors*,language_code`|

    For the `authors*` facet, adding a `*` after a field name denotes that the field is of type `Collection(Edm.String)`. This allows the Azure Function to add filters correctly to queries. 

1. Select **Save** to save the settings. 

1. Return to Visual Studio Code. 

1. Refresh your Static web app to see the Static web app's application settings. 

## Run queries in your app

1. In Visual Studio Code, select **Azure** from the Activity Bar.

1. In the Side bar, **right-click on your Azure subscription** under the `Static web apps` area and find the Static web app you created.

1. Right-click the Static Web App name and select **Browse site**.

1. Select **Open** in the pop-up dialog.

1. In the website search bar, enter a search query such as `code`, _slowly_ so the suggest feature suggests book titles. Select a suggestion or continue entering your own query. Press enter when you've completed your search query. 

1. Review the results then select one of the books to see more details. 

## Clean up

If you no longer need Azure Cognitive Search or Azure Static Web Apps, remember to delete both resources in your subscription.
