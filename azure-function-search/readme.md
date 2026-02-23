---
page_type: sample
languages:
  - python
name: "Create an Azure function that specifies queries using Python"
description: |
  Creates an Azure function that formulates queries, document lookup, and suggestions for typeahead queries.
products:
  - azure
  - azure-cognitive-search
  - azure-functions
urlFragment: python-azure-function-search
---

# Create an Azure function that specifies queries using Python

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

This sample provides an Azure function that formulates queries, document lookup, and suggestions for typeahead queries against an Azure AI Search index.

## What's in this sample

| File | Description |
|------|-------------|
| `function_app.py` | Main Azure Functions entry point |
| `search.py` | Handles search query requests |
| `lookup.py` | Handles document lookup requests |
| `suggest.py` | Handles typeahead suggestion requests |
| `host.json` | Azure Functions host configuration |
| `requirements.txt` | Python package dependencies |
| `local.settings.json.rename` | Template for local settings configuration |
| `shared_code/` | Shared utility code |

## Documentation

This sample is the Python version of the `api` content used in [Tutorial: Add search to web apps](https://learn.microsoft.com/azure/search/tutorial-csharp-overview). You can substitute this code to create a Python version of the sample app.

## Next step

You can learn more about Azure AI Search on the [official documentation site](https://learn.microsoft.com/azure/search).
