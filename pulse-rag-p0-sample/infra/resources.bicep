// =============================================================================
// resources.bicep - all per-environment resources for the Pulse RAG P0 sample
// =============================================================================

param location string
param environmentName string
param principalId string
param openAiLocation string
param chatModelName string
param chatModelVersion string
param embeddingModelName string
param embeddingModelVersion string
param tags object

// -----------------------------------------------------------------------------
// Naming
// -----------------------------------------------------------------------------
var suffix = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var nameShort = take('${toLower(environmentName)}${suffix}', 18)

var logAnalyticsName = 'log-${nameShort}'
var appInsightsName = 'appi-${nameShort}'
var storageName = take('st${replace(nameShort, '-', '')}', 24)
var cosmosName = 'cosmos-${nameShort}'
var searchName = 'srch-${nameShort}'
var openAiName = 'oai-${nameShort}'
var foundryName = 'aifnd-${nameShort}'
var foundryProjectName = 'proj-${nameShort}'
var planName = 'plan-${nameShort}'
var functionAppName = 'func-${nameShort}'
var webAppName = 'web-${nameShort}'
var uamiName = 'id-${nameShort}'
var dlqQueueName = 'pulse-rag-indexing-dlq'

// -----------------------------------------------------------------------------
// Observability
// -----------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// -----------------------------------------------------------------------------
// Managed identity (shared by api + web)
// -----------------------------------------------------------------------------
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: uamiName
  location: location
  tags: tags
}

// -----------------------------------------------------------------------------
// Storage (Functions runtime + DLQ queue)
// -----------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true // Required by Functions consumption plan today
  }
}

resource storageQueueService 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource dlqQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = {
  parent: storageQueueService
  name: dlqQueueName
}

// -----------------------------------------------------------------------------
// Cosmos DB (SQL API)
// -----------------------------------------------------------------------------
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-08-15' = {
  name: cosmosName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    disableLocalAuth: false
    capabilities: []
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  parent: cosmos
  name: 'pulse-rag'
  properties: {
    resource: { id: 'pulse-rag' }
    options: { throughput: 400 }
  }
}

resource devicesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDb
  name: 'devices'
  properties: {
    resource: {
      id: 'devices'
      partitionKey: { paths: ['/tenantId'], kind: 'Hash' }
    }
  }
}

resource leasesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-08-15' = {
  parent: cosmosDb
  name: 'leases'
  properties: {
    resource: {
      id: 'leases'
      partitionKey: { paths: ['/id'], kind: 'Hash' }
    }
  }
}

// -----------------------------------------------------------------------------
// Azure AI Search
// -----------------------------------------------------------------------------
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  tags: tags
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'free'
    authOptions: null
    disableLocalAuth: true
  }
}

// -----------------------------------------------------------------------------
// Azure OpenAI (chat + embedding deployments)
// -----------------------------------------------------------------------------
resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: openAiLocation
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: chatModelName
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: chatModelName, version: chatModelVersion }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: embeddingModelName
  sku: { name: 'Standard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: embeddingModelName, version: embeddingModelVersion }
  }
  dependsOn: [chatDeployment]
}

// -----------------------------------------------------------------------------
// Azure AI Foundry (AIServices account + project)
// -----------------------------------------------------------------------------
resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: foundryName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: foundryName
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
    disableLocalAuth: false
  }
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: foundryProjectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {}
}

// -----------------------------------------------------------------------------
// App Service plan (Linux) + Function App (api) + Web App (web)
// -----------------------------------------------------------------------------
resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  tags: tags
  sku: { name: 'B1', tier: 'Basic' }
  kind: 'linux'
  properties: { reserved: true }
}

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: functionAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${uami.id}': {} }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    keyVaultReferenceIdentity: uami.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'AzureWebJobsFeatureFlags', value: 'EnableWorkerIndexing' }
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
        { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
        { name: 'AzureWebJobsStorage__clientId', value: uami.properties.clientId }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        { name: 'COSMOS_DATABASE_NAME', value: 'pulse-rag' }
        { name: 'COSMOS_CONTAINER_NAME', value: 'devices' }
        { name: 'COSMOS_LEASE_CONTAINER_NAME', value: 'leases' }
        { name: 'COSMOS_CONNECTION__accountEndpoint', value: cosmos.properties.documentEndpoint }
        { name: 'COSMOS_CONNECTION__credential', value: 'managedidentity' }
        { name: 'COSMOS_CONNECTION__clientId', value: uami.properties.clientId }
        { name: 'SearchServiceEndpoint', value: 'https://${search.name}.search.windows.net' }
        { name: 'SearchServiceName', value: search.name }
        { name: 'SearchIndexName', value: 'pulse-device-chunks' }
        { name: 'AzureOpenAIEndpoint', value: openAi.properties.endpoint }
        { name: 'AzureOpenAIEmbeddingDeployment', value: embeddingModelName }
        { name: 'AzureOpenAIApiVersion', value: '2024-10-21' }
        { name: 'AZURE_CLIENT_ID', value: uami.properties.clientId }
        { name: 'DLQ_QUEUE_NAME', value: dlqQueueName }
        { name: 'ChunkSize', value: '1000' }
        { name: 'ChunkOverlap', value: '150' }
      ]
    }
  }
}

resource webApp 'Microsoft.Web/sites@2024-04-01' = {
  name: webAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  kind: 'app,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${uami.id}': {} }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
      appCommandLine: 'gunicorn --bind=0.0.0.0:8000 --timeout 120 server:app'
      appSettings: [
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'PORT', value: '8000' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        { name: 'PROJECT_ENDPOINT', value: '${foundry.properties.endpoint}api/projects/${foundryProject.name}' }
        { name: 'CHAT_MODEL_DEPLOYMENT', value: chatModelName }
        { name: 'EMBEDDING_DEPLOYMENT', value: embeddingModelName }
        { name: 'SearchServiceEndpoint', value: 'https://${search.name}.search.windows.net' }
        { name: 'SearchIndexName', value: 'pulse-device-chunks' }
        { name: 'RETRIEVAL_TOP_K', value: '5' }
        { name: 'AGENT_NAME', value: '' }
        { name: 'AZURE_CLIENT_ID', value: uami.properties.clientId }
        { name: 'FLASK_SESSION_SECRET', value: uniqueString(subscription().id, resourceGroup().id, 'flask') }
      ]
    }
  }
}

// =============================================================================
// RBAC role assignments
// =============================================================================

// Built-in role ids
var roles = {
  storageBlobDataOwner: 'b7e6dc6d-f1e8-4753-8033-0f0351f01cb5'
  storageQueueDataContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  storageQueueDataMessageSender: 'c6a89b2d-59bc-44d0-9896-0f6e12d7b80a'
  searchIndexDataContributor: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchServiceContributor: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  azureAIDeveloper: '64702f94-c441-49e6-a78b-ef80e0188fee'
  // Cosmos SQL data-plane role (built-in: Cosmos DB Built-in Data Contributor)
  cosmosDataContributor: '00000000-0000-0000-0000-000000000002'
}

resource raStorageBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, uami.id, roles.storageBlobDataOwner)
  scope: storage
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataOwner)
  }
}

resource raStorageQueue 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, uami.id, roles.storageQueueDataContributor)
  scope: storage
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageQueueDataContributor)
  }
}

resource raSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, uami.id, roles.searchIndexDataContributor)
  scope: search
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
  }
}

resource raSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, uami.id, roles.searchServiceContributor)
  scope: search
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchServiceContributor)
  }
}

resource raOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, uami.id, roles.cognitiveServicesOpenAIUser)
  scope: openAi
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesOpenAIUser)
  }
}

resource raFoundryDev 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, uami.id, roles.azureAIDeveloper)
  scope: foundry
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.azureAIDeveloper)
  }
}

resource raFoundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, uami.id, roles.cognitiveServicesUser)
  scope: foundry
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesUser)
  }
}

// Cosmos data-plane RBAC (data role assignment, distinct from ARM RBAC)
resource cosmosRoleUami 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-08-15' = {
  parent: cosmos
  name: guid(cosmos.id, uami.id, roles.cosmosDataContributor)
  properties: {
    principalId: uami.properties.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${roles.cosmosDataContributor}'
    scope: cosmos.id
  }
}

// -----------------------------------------------------------------------------
// Optional: grant deploying principal the same data-plane roles for local dev
// -----------------------------------------------------------------------------
var grantPrincipal = !empty(principalId)

resource raSearchDataPrincipal 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPrincipal) {
  name: guid(search.id, principalId, roles.searchIndexDataContributor)
  scope: search
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchIndexDataContributor)
  }
}

resource raSearchServicePrincipal 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPrincipal) {
  name: guid(search.id, principalId, roles.searchServiceContributor)
  scope: search
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.searchServiceContributor)
  }
}

resource raOpenAiPrincipal 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPrincipal) {
  name: guid(openAi.id, principalId, roles.cognitiveServicesOpenAIUser)
  scope: openAi
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.cognitiveServicesOpenAIUser)
  }
}

resource raFoundryDevPrincipal 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPrincipal) {
  name: guid(foundry.id, principalId, roles.azureAIDeveloper)
  scope: foundry
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.azureAIDeveloper)
  }
}

resource cosmosRolePrincipal 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-08-15' = if (grantPrincipal) {
  parent: cosmos
  name: guid(cosmos.id, principalId, roles.cosmosDataContributor)
  properties: {
    principalId: principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${roles.cosmosDataContributor}'
    scope: cosmos.id
  }
}

// =============================================================================
// Outputs
// =============================================================================
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosDatabaseName string = cosmosDb.name
output cosmosContainerName string = devicesContainer.name
output cosmosLeaseContainerName string = leasesContainer.name
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output searchServiceName string = search.name
output openAiEndpoint string = openAi.properties.endpoint
output foundryProjectEndpoint string = '${foundry.properties.endpoint}api/projects/${foundryProject.name}'
output functionAppName string = functionApp.name
output webAppName string = webApp.name
output webAppUri string = 'https://${webApp.properties.defaultHostName}'
output dlqQueueName string = dlqQueueName
