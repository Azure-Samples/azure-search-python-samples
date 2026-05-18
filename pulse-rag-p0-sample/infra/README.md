# Infrastructure for the Pulse RAG P0 sample

This folder deploys everything the sample needs via the Azure Developer CLI (`azd`):

| Resource                                                                               | Purpose                                                                                                                                                                                                                                                                   |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Azure Cosmos DB** (`pulse-rag` database, `devices` + `leases` containers)            | System of record for device documents. The `leases` container backs the change feed processor used by the Function App.                                                                                                                                                   |
| **Azure AI Search** (Basic, RBAC auth, vector + semantic features)                     | Stores chunked + vectorized device content. Schema in [`index/pulse-device-chunks.json`](index/pulse-device-chunks.json).                                                                                                                                                 |
| **Azure Storage** (StorageV2 LRS, shared-key disabled, RBAC only)                      | Functions runtime account, plus the `pulse-rag-indexing-dlq` queue used by the per-document DLQ.                                                                                                                                                                          |
| **Azure AI Foundry** (AIServices account + project + model deployments)                | Single endpoint serving both the chat path (Flask app -> `AIProjectClient` -> OpenAI Responses) and the embedding path (Function App -> `AzureOpenAI` client -> `text-embedding-3-small`). Hosts `gpt-4o-mini` (chat) and `text-embedding-3-small` (1536-dim embeddings). |
| **Azure Container Apps Environment** (`cae-*`) + **Azure Container Registry** (`acr*`) | Hosting platform for both containers. `azd deploy` does a remote build into ACR.                                                                                                                                                                                          |
| **Container App: `func-*`** (`azd-service-name: api`)                                  | Hosts the Cosmos change-feed trigger and HTTP endpoints from `api/`. Identity-based `AzureWebJobsStorage`.                                                                                                                                                                |
| **Container App: `web-*`** (`azd-service-name: web`)                                   | Hosts the Flask chat app from `app/`. Runs `gunicorn server:app`.                                                                                                                                                                                                         |
| **User-assigned managed identity**                                                     | Single identity attached to both container apps and to ACR. Holds all data-plane role assignments.                                                                                                                                                                        |
| **Log Analytics + Application Insights**                                               | Telemetry for both apps.                                                                                                                                                                                                                                                  |

## Role assignments

The managed identity (and, when `AZURE_PRINCIPAL_ID` is set, the deploying user) gets:

- Cosmos DB Built-in Data Contributor (SQL data-plane role) on the Cosmos account
- Search Index Data Contributor + Search Service Contributor on the search service
- Storage Blob Data Owner + Storage Queue Data Contributor + Storage Table Data Contributor on the storage account (required for identity-based `AzureWebJobsStorage`)
- Cognitive Services OpenAI User + Azure AI Developer + Cognitive Services User on the Foundry AIServices account (covers both Responses API and embeddings inference)

## Deploy

From the `pulse-rag-p0-sample/` folder:

```pwsh
azd auth login
azd up
```

`azd up` will prompt for:

1. An environment name (used to suffix resource names).
2. A location for most resources.
3. A model-deployment region for the Foundry account (defaults to `eastus2` — change via `azd env set AZURE_OPENAI_LOCATION <region>` if your subscription is restricted to other regions for `gpt-4o-mini` / `text-embedding-3-small` capacity).

After provisioning, the `postprovision` hook in [`azure.yaml`](../azure.yaml) calls [`scripts/create_index.py`](../scripts/create_index.py) to create the AI Search index from the JSON schema, then prints the seed command.

## Tear down

```pwsh
azd down --purge
```

`--purge` is important: the Foundry AIServices account goes into soft-delete by default and will prevent redeploying with the same name.
