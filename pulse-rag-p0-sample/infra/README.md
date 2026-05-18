# Infrastructure for the Pulse RAG P0 sample

This folder deploys everything the sample needs via the Azure Developer CLI (`azd`):

| Resource | Purpose |
| --- | --- |
| **Azure Cosmos DB** (`pulse-rag` database, `devices` + `leases` containers) | System of record for device documents. The `leases` container backs the change feed processor used by the Function App. |
| **Azure AI Search** (Basic, RBAC auth, vector + semantic features) | Stores chunked + vectorized device content. Schema in [`index/pulse-device-chunks.json`](index/pulse-device-chunks.json). |
| **Azure Storage** (StorageV2 LRS) | Functions runtime account, plus the `pulse-rag-indexing-dlq` queue used by the per-document DLQ. |
| **Azure OpenAI** (S0) | `gpt-4o-mini` chat deployment + `text-embedding-3-small` embedding deployment (1536 dims). |
| **Azure AI Foundry** (AIServices account + project) | Project endpoint the Flask chat app uses to call OpenAI Responses via the Foundry conversations API. |
| **Function App** (Linux, B1 plan, `azd-service-name: api`) | Hosts the change-feed trigger and HTTP endpoints from `api/`. |
| **App Service** (Linux Python 3.11, same plan, `azd-service-name: web`) | Hosts the Flask chat app from `app/`. Runs `gunicorn server:app`. |
| **User-assigned managed identity** | Single identity attached to both apps. Holds all data-plane role assignments. |
| **Log Analytics + Application Insights** | Telemetry for both apps. |

## Role assignments

The managed identity (and, when `AZURE_PRINCIPAL_ID` is set, the deploying user) gets:

- Cosmos DB Built-in Data Contributor (SQL data-plane role) on the Cosmos account
- Search Index Data Contributor + Search Service Contributor on the search service
- Storage Blob Data Owner + Storage Queue Data Contributor on the storage account
- Cognitive Services OpenAI User on the Azure OpenAI account
- Azure AI Developer + Cognitive Services User on the Foundry AIServices account

## Deploy

From the `pulse-rag-p0-sample/` folder:

```pwsh
azd auth login
azd up
```

`azd up` will prompt for:

1. An environment name (used to suffix resource names).
2. A location for most resources.
3. An Azure OpenAI region (defaults to `eastus2` — change via `azd env set AZURE_OPENAI_LOCATION <region>` if your subscription is restricted).

After provisioning, the `postprovision` hook in [`azure.yaml`](../azure.yaml) calls [`scripts/create_index.py`](../scripts/create_index.py) to create the AI Search index from the JSON schema, then prints the seed command.

## Tear down

```pwsh
azd down --purge
```

`--purge` is important: Azure OpenAI and AI Foundry accounts go into soft-delete by default and prevent redeploying with the same name.
