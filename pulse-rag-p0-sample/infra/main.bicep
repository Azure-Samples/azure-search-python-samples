// =============================================================================
// Pulse RAG P0 sample - infrastructure
// =============================================================================
// Deploys:
//   - Log Analytics + Application Insights
//   - Azure Storage (Functions runtime + DLQ queue)
//   - Azure Cosmos DB (database + devices container + leases container)
//   - Azure AI Search (Basic, RBAC auth)
//   - Azure OpenAI (chat + embedding deployments)
//   - Azure AI Foundry (AIServices account + project)
//   - User-assigned managed identity (shared by api + web)
//   - RBAC role assignments
//   - Linux Consumption Function App (api)
//   - Linux App Service (Python) for the chat app (web)
// =============================================================================

targetScope = 'subscription'

@description('A short alpha-numeric environment name used as a suffix for resource names.')
@minLength(1)
@maxLength(12)
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Object id of the deploying user / service principal. Granted data-plane roles for local dev.')
param principalId string = ''

@description('Region for the Azure OpenAI resource. Many embedding/chat models are limited to a subset of regions.')
param openAiLocation string = 'eastus2'

@description('Region for Cosmos DB. Override if the primary region is capacity-constrained.')
param cosmosLocation string = location

@description('Azure OpenAI chat model name.')
param chatModelName string = 'gpt-4o-mini'

@description('Azure OpenAI chat model version.')
param chatModelVersion string = '2024-07-18'

@description('Azure OpenAI embedding model name.')
param embeddingModelName string = 'text-embedding-3-small'

@description('Azure OpenAI embedding model version.')
param embeddingModelVersion string = '1'

var rgName = 'rg-${environmentName}'
var tags = { 'azd-env-name': environmentName, sample: 'pulse-rag-p0-sample' }

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    principalId: principalId
    openAiLocation: openAiLocation
    cosmosLocation: cosmosLocation
    chatModelName: chatModelName
    chatModelVersion: chatModelVersion
    embeddingModelName: embeddingModelName
    embeddingModelVersion: embeddingModelVersion
    tags: tags
  }
}

// =============================================================================
// Outputs consumed by azd (env vars for `api` and `web` services)
// =============================================================================

output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name

// Cosmos
output COSMOS_ENDPOINT string = resources.outputs.cosmosEndpoint
output COSMOS_DATABASE_NAME string = resources.outputs.cosmosDatabaseName
output COSMOS_CONTAINER_NAME string = resources.outputs.cosmosContainerName
output COSMOS_LEASE_CONTAINER_NAME string = resources.outputs.cosmosLeaseContainerName
output COSMOS_CONNECTION__accountEndpoint string = resources.outputs.cosmosEndpoint

// Search
output SearchServiceEndpoint string = resources.outputs.searchEndpoint
output SearchServiceName string = resources.outputs.searchServiceName
output SearchIndexName string = 'pulse-device-chunks'

// OpenAI / embeddings (Function App reads these to vectorize chunks)
output AzureOpenAIEndpoint string = resources.outputs.openAiEndpoint
output AzureOpenAIEmbeddingDeployment string = embeddingModelName
output AzureOpenAIApiVersion string = '2024-10-21'

// Foundry project endpoint (chat app)
output PROJECT_ENDPOINT string = resources.outputs.foundryProjectEndpoint
output CHAT_MODEL_DEPLOYMENT string = chatModelName
output EMBEDDING_DEPLOYMENT string = embeddingModelName

// DLQ + chunking knobs
output DLQ_QUEUE_NAME string = resources.outputs.dlqQueueName
output ChunkSize string = '1000'
output ChunkOverlap string = '150'

// App URLs
output API_FUNCTION_APP_NAME string = resources.outputs.functionAppName
output WEB_APP_NAME string = resources.outputs.webAppName
output WEB_URI string = resources.outputs.webAppUri

// Container Registry (azd uses these to build & push images)
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.containerRegistryEndpoint
output AZURE_CONTAINER_REGISTRY_NAME string = resources.outputs.containerRegistryName
