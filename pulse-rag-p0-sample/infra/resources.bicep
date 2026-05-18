// =============================================================================
// resources.bicep - all per-environment resources for the Pulse RAG P0 sample
// =============================================================================

param location string
param environmentName string
param principalId string
param openAiLocation string
param cosmosLocation string = location
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
var acaEnvName = 'cae-${nameShort}'
var acrName = take('acr${replace(nameShort, '-', '')}', 50)
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
  // SecurityControl=Ignore exempts this account from the org policy that disables
  // public network access. Required because Container Apps Consumption profile
  // has no VNet integration / private endpoint path to reach storage. Data plane
  // is still locked down: shared keys disabled, AAD/RBAC + managed identity only.
  tags: union(tags, { SecurityControl: 'Ignore' })
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
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
  location: cosmosLocation
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: cosmosLocation
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    disableLocalAuth: false
    capabilities: [
      { name: 'EnableServerless' }
    ]
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-08-15' = {
  parent: cosmos
  name: 'pulse-rag'
  properties: {
    resource: { id: 'pulse-rag' }
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
// Azure AI Foundry (AIServices account + project + model deployments)
// AIServices (kind=AIServices) exposes both the Foundry projects API surface
// AND the Azure OpenAI inference API surface, so chat + embedding deployments
// live here and are reachable by both AIProjectClient (web) and AzureOpenAI
// client (function app for embeddings).
// -----------------------------------------------------------------------------
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: foundryName
  location: openAiLocation
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
  location: openAiLocation
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {}
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: chatModelName
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: chatModelName, version: chatModelVersion }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: embeddingModelName
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: embeddingModelName, version: embeddingModelVersion }
  }
  dependsOn: [chatDeployment]
}

// -----------------------------------------------------------------------------
// Container Registry (azd pushes built images here)
// -----------------------------------------------------------------------------
resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// -----------------------------------------------------------------------------
// Container Apps Environment + apps (api Function on ACA, web Container App)
// Container Apps avoids the App Service VM-core preflight that blocks this
// subscription, while still giving us serverless containers with managed
// identity, scale-to-N, and built-in HTTPS ingress.
// -----------------------------------------------------------------------------
resource acaEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: acaEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      { name: 'Consumption', workloadProfileType: 'Consumption' }
    ]
  }
}

// Placeholder image used until azd builds + deploys the real one.
var placeholderImage = 'mcr.microsoft.com/k8se/quickstart:latest'

resource functionApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: functionAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${uami.id}': {} }
  }
  properties: {
    managedEnvironmentId: acaEnv.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: uami.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: placeholderImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
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
            { name: 'AzureOpenAIEndpoint', value: foundry.properties.endpoint }
            { name: 'AzureOpenAIEmbeddingDeployment', value: embeddingModelName }
            { name: 'AzureOpenAIApiVersion', value: '2024-10-21' }
            { name: 'AZURE_CLIENT_ID', value: uami.properties.clientId }
            { name: 'DLQ_QUEUE_NAME', value: dlqQueueName }
            { name: 'ChunkSize', value: '1000' }
            { name: 'ChunkOverlap', value: '150' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource webApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: webAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${uami.id}': {} }
  }
  properties: {
    managedEnvironmentId: acaEnv.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: uami.id
        }
      ]
      secrets: [
        {
          name: 'flask-session-secret'
          value: uniqueString(subscription().id, resourceGroup().id, 'flask')
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: placeholderImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
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
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DATABASE_NAME', value: 'pulse-rag' }
            { name: 'COSMOS_CONTAINER_NAME', value: 'devices' }
            { name: 'DEMO_DEFAULT_TENANT_ID', value: 'contoso' }
            { name: 'FLASK_SESSION_SECRET', secretRef: 'flask-session-secret' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// =============================================================================
// RBAC role assignments
// =============================================================================

// Built-in role ids
var roles = {
  storageBlobDataOwner: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b' // Storage Blob Data Owner (required by AzureWebJobsStorage identity-based)
  storageTableDataContributor: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
  storageQueueDataContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  storageQueueDataMessageSender: 'c6a89b2d-59bc-44d0-9896-0f6e12d7b80a'
  searchIndexDataContributor: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchServiceContributor: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  azureAIDeveloper: '64702f94-c441-49e6-a78b-ef80e0188fee'
  // Cosmos SQL data-plane role (built-in: Cosmos DB Built-in Data Contributor)
  cosmosDataContributor: '00000000-0000-0000-0000-000000000002'
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
}

resource raAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, uami.id, roles.acrPull)
  scope: registry
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPull)
  }
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
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.storageQueueDataContributor
    )
  }
}

resource raStorageTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, uami.id, roles.storageTableDataContributor)
  scope: storage
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.storageTableDataContributor
    )
  }
}

resource raSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, uami.id, roles.searchIndexDataContributor)
  scope: search
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.searchIndexDataContributor
    )
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

resource raFoundryOpenAI 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, uami.id, roles.cognitiveServicesOpenAIUser)
  scope: foundry
  properties: {
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.cognitiveServicesOpenAIUser
    )
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
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.searchIndexDataContributor
    )
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

resource raFoundryOpenAIPrincipal 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPrincipal) {
  name: guid(foundry.id, principalId, roles.cognitiveServicesOpenAIUser)
  scope: foundry
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      roles.cognitiveServicesOpenAIUser
    )
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
output openAiEndpoint string = foundry.properties.endpoint
output foundryProjectEndpoint string = '${foundry.properties.endpoint}api/projects/${foundryProject.name}'
output functionAppName string = functionApp.name
output webAppName string = webApp.name
output webAppUri string = 'https://${webApp.properties.configuration.ingress.fqdn}'
output dlqQueueName string = dlqQueueName
output containerRegistryEndpoint string = registry.properties.loginServer
output containerRegistryName string = registry.name
