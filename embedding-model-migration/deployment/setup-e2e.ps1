#requires -Version 7.2
<#
.SYNOPSIS
Configure MI/RBAC/EasyAuth and optionally deploy the embedding Function with Entra.
.DESCRIPTION
Existing resources: Python Flex app, host storage, Search service, private source
container, and Foundry/Azure OpenAI model deployments. No credentials are accepted.
Use -CreateFunctionApp to create a NEW dedicated FC1 plan and Python Function on
the supplied storage account, without retrieving its keys. Other resource creation
and model deployment is intentionally explicit, outside this script: check model
availability, quotas, and GlobalStandard support in the target region first.
The existing single-tenant API app registration must expose api://<client-id>.
Requires Azure CLI login, resource write permissions, and role-assignment write.
With -EnableLocalCliAccess, API app registration update permissions are also needed.
Authentication is configured BEFORE application code is deployed.
Neither shared storage accounts nor shared Foundry/Search service auth settings
are globally changed. Does not grant local users broad Search data access.
Deployment uses the same Entra-only Flex OneDeploy SCM endpoint as current Azure
CLI: POST /api/publish?RemoteBuild=true. No publish profile or SCM password.
Source: azure-cli custom.py enable_zip_deploy_flex / get_scm_site_headers_flex.
References:
https://learn.microsoft.com/azure/azure-functions/flex-consumption-how-to
https://learn.microsoft.com/azure/azure-functions/manage-connections?pivots=functions-auth-identity&tabs=host
https://learn.microsoft.com/azure/search/search-how-to-managed-identities-storage
https://learn.microsoft.com/azure/app-service/deploy-zip
.EXAMPLE
.\setup-e2e.ps1 -SubscriptionId '<subscription-guid>' -TenantId '<tenant-guid>' `
  -ResourceGroup '<rg>' -FunctionApp '<app>' -ApiApplicationClientId '<api-client-guid>' `
  -HostStorageResourceId '<storage-account-resource-id>' -SearchResourceId '<search-resource-id>' `
  -SourceStorageResourceId '<source-storage-account-resource-id>' -SourceContainer documents `
  -FoundryResourceIds '<foundry-resource-id>' -BaselineEndpoint 'https://<account>.openai.azure.com' `
  -CohereEndpoint 'https://<account>.services.ai.azure.com/providers/cohere/v2/embed' `
  -FastDeployment '<fast-deployment>' -ProDeployment '<pro-deployment>' -PrintConfiguration
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][guid]$TenantId,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$FunctionApp,
    [Parameter(Mandatory)][guid]$ApiApplicationClientId,
    [Parameter(Mandatory)][string]$HostStorageResourceId,
    [Parameter(Mandatory)][string]$SearchResourceId,
    [Parameter(Mandatory)][string]$SourceStorageResourceId,
    [Parameter(Mandatory)][string]$SourceContainer,
    [Parameter(Mandatory)][string[]]$FoundryResourceIds,
    [Parameter(Mandatory)][string]$BaselineEndpoint,
    [Parameter(Mandatory)][string]$CohereEndpoint,
    [Parameter(Mandatory)][string]$FastDeployment,
    [Parameter(Mandatory)][string]$ProDeployment,
    [string]$BaselineDeployment = 'text-embedding-3-small',
    [int]$FastDimensions = 1024,
    [int]$ProDimensions = 1024,
    [guid[]]$TestUserObjectIds = @(),
    [switch]$EnableLocalCliAccess,
    [string]$ApplicationInsightsResourceId,
    [switch]$CreateFunctionApp,
    [string]$Location,
    [string]$PlanName,
    [string]$DeploymentContainer,
    [string]$PythonVersion = '3.11',
    [string]$PackagePath,
    [ValidateRange(0, 900)][int]$RbacPropagationSeconds = 120,
    [ValidateRange(60, 3600)][int]$DeploymentTimeoutSeconds = 900,
    [switch]$PrintConfiguration
)
$ErrorActionPreference = 'Stop'
foreach ($endpoint in @($BaselineEndpoint, $CohereEndpoint)) {
    $uri = [uri]$endpoint
    if ($uri.Scheme -ne 'https' -or -not $uri.Host -or $uri.Query -or $uri.Fragment -or $uri.UserInfo) {
        throw 'Model endpoints must be HTTPS without credentials, queries, or fragments.'
    }
}
if (-not $CohereEndpoint.TrimEnd('/').EndsWith('/providers/cohere/v2/embed')) {
    throw 'CohereEndpoint must end in /providers/cohere/v2/embed.'
}
if ($FastDimensions -lt 1 -or $ProDimensions -lt 1) { throw 'Embedding dimensions must be positive.' }
if ($SourceContainer -notmatch '^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$' -or $SourceContainer.Contains('--')) {
    throw 'SourceContainer must be a valid Azure blob container name.'
}
$sourceScope = "$SourceStorageResourceId/blobServices/default/containers/$SourceContainer"
$settings = @(
    "BASELINE_ENDPOINT=$($BaselineEndpoint.TrimEnd('/'))", "BASELINE_DEPLOYMENT=$BaselineDeployment",
    "COHERE_ENDPOINT=$($CohereEndpoint.TrimEnd('/'))", "FAST_DEPLOYMENT=$FastDeployment",
    "PRO_DEPLOYMENT=$ProDeployment", "FAST_DIMENSIONS=$FastDimensions", "PRO_DIMENSIONS=$ProDimensions",
    'REQUIRE_ENTRA_AUTH=true'
)
if ($PrintConfiguration) {
    @{
        operations = @('Optional dedicated Python FC1 creation', 'Search system MI',
            'Function system MI', 'Function -> models: Cognitive Services User (each supplied account)',
            'Search -> source: Storage Blob Data Reader (container scope)',
            'Required EasyAuth allowlist before code', 'Convert host/deployment storage to MI',
            'Disable SCM/FTP basic publishing authentication on this app',
            'Optional Entra OneDeploy remote build + deployment polling')
        applicationSettings = $settings
        dataSource = @{
            type = 'azureblob'
            credentials = @{ connectionString = "ResourceId=$SourceStorageResourceId;" }
            container = @{ name = $SourceContainer }
        }
        customSkill = @{ authResourceId = "api://$ApiApplicationClientId"; authIdentity = 'Omit to use Search system MI' }
        sourceReaderScope = $sourceScope
        note = 'Model deployments must already exist (use GlobalStandard where supported). This is configuration, not a completed indexing test.'
    } | ConvertTo-Json -Depth 15
    return
}
function Invoke-AzJson([string[]]$Arguments) {
    $result = & az @Arguments --only-show-errors --output json 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI operation failed ($($Arguments[0])); output suppressed to protect credentials." }
    if ($result) { ($result -join "`n") | ConvertFrom-Json -AsHashtable }
}
function Write-ArmJson([string]$Url, [string]$Method, $Body) {
    $path = Join-Path $PSScriptRoot ('.setup-payload-' + [guid]::NewGuid() + '.json')
    try {
        [IO.File]::WriteAllText($path, ($Body | ConvertTo-Json -Depth 50), [Text.UTF8Encoding]::new($false))
        Invoke-AzJson @('rest', '--method', $Method, '--url', $Url, '--body', "@$path")
    }
    finally { if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force } }
}
function Grant-Role([string]$Principal, [string]$Scope, [string]$Role) {
    $assignments = @(Invoke-AzJson @('role', 'assignment', 'list', '--assignee-object-id', $Principal, '--scope', $Scope))
    if (-not ($assignments | Where-Object { $_.scope -ieq $Scope -and $_.roleDefinitionId.EndsWith("/$Role") })) {
        Invoke-AzJson @('role', 'assignment', 'create', '--assignee-object-id', $Principal,
            '--assignee-principal-type', 'ServicePrincipal', '--role', $Role, '--scope', $Scope) | Out-Null
    }
}
$account = Invoke-AzJson @('account', 'show', '--subscription', $SubscriptionId.ToString())
if ($account.tenantId -ne $TenantId.ToString()) { throw 'Selected subscription belongs to a different tenant.' }
$appId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$FunctionApp"
$appUrl = "https://management.azure.com${appId}?api-version=2024-04-01"
if ($CreateFunctionApp) {
    if (-not $Location -or -not $PlanName -or -not $DeploymentContainer) {
        throw '-CreateFunctionApp requires Location, PlanName, and DeploymentContainer (unique to this app).'
    }
    $existing = @(Invoke-AzJson @('resource', 'list', '--subscription', $SubscriptionId.ToString(),
        '--resource-group', $ResourceGroup, '--query', "[?name=='$FunctionApp' || name=='$PlanName'].id"))
    if ($existing.Count) { throw 'Creation refuses to overwrite an existing app or plan. Omit -CreateFunctionApp to configure it.' }
    if ($DeploymentContainer -notmatch '^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$' -or $DeploymentContainer.Contains('--')) {
        throw 'DeploymentContainer must be a valid Azure blob container name.'
    }
    $containers = Invoke-AzJson @('rest', '--method', 'GET', '--url',
        "https://management.azure.com$HostStorageResourceId/blobServices/default/containers?api-version=2023-05-01")
    if (@($containers.value | Where-Object { $_.name -eq $DeploymentContainer }).Count) {
        throw 'Deployment container already exists. Supply a NEW container dedicated to this app.'
    }
    Write-ArmJson "https://management.azure.com$HostStorageResourceId/blobServices/default/containers/${DeploymentContainer}?api-version=2023-05-01" 'PUT' @{
        properties = @{ publicAccess = 'None' }
    } | Out-Null
    $storage = Invoke-AzJson @('rest', '--method', 'GET', '--url',
        "https://management.azure.com${HostStorageResourceId}?api-version=2023-05-01")
    $planId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/serverfarms/$PlanName"
    Write-ArmJson "https://management.azure.com${planId}?api-version=2024-04-01" 'PUT' @{
        location = $Location; kind = 'functionapp'; sku = @{ name = 'FC1'; tier = 'FlexConsumption' }
        properties = @{ reserved = $true }
    } | Out-Null
    Write-ArmJson $appUrl 'PUT' @{
        location = $Location; kind = 'functionapp,linux'; identity = @{ type = 'SystemAssigned' }
        properties = @{
            serverFarmId = $planId; httpsOnly = $true
            siteConfig = @{ minTlsVersion = '1.2' }
            functionAppConfig = @{
                runtime = @{ name = 'python'; version = $PythonVersion }
                scaleAndConcurrency = @{ maximumInstanceCount = 40; instanceMemoryMB = 2048 }
                deployment = @{ storage = @{
                    type = 'blobContainer'; value = "$($storage.properties.primaryEndpoints.blob)$DeploymentContainer"
                    authentication = @{ type = 'SystemAssignedIdentity' }
                } }
            }
        }
    } | Out-Null
}
$searchUrl = "https://management.azure.com${SearchResourceId}?api-version=2023-11-01"
$search = Invoke-AzJson @('rest', '--method', 'GET', '--url', $searchUrl)
if (-not $search.identity.principalId) {
    $identity = if ($search.identity) { $search.identity } else { @{} }
    $identity.type = if ($identity.userAssignedIdentities.Count) { 'SystemAssigned, UserAssigned' } else { 'SystemAssigned' }
    Write-ArmJson $searchUrl 'PATCH' @{ identity = $identity } | Out-Null
    $search = Invoke-AzJson @('rest', '--method', 'GET', '--url', $searchUrl)
}
$authArguments = @{
    ResourceGroup = $ResourceGroup; FunctionApp = $FunctionApp; SubscriptionId = $SubscriptionId
    TenantId = $TenantId; ApiApplicationClientId = $ApiApplicationClientId
    SearchIdentityObjectId = [guid]$search.identity.principalId
    TestUserObjectIds = $TestUserObjectIds; EnableLocalCliAccess = $EnableLocalCliAccess
}
& (Join-Path $PSScriptRoot '..\function\configure-entra-auth.ps1') @authArguments
& (Join-Path $PSScriptRoot 'configure-keyless-hosting.ps1') -ResourceGroup $ResourceGroup `
    -FunctionApp $FunctionApp -SubscriptionId $SubscriptionId -HostStorageResourceId $HostStorageResourceId `
    -ApplicationInsightsResourceId $ApplicationInsightsResourceId -RbacPropagationSeconds $RbacPropagationSeconds
$app = Invoke-AzJson @('rest', '--method', 'GET', '--url', $appUrl)
foreach ($resourceId in ($FoundryResourceIds | Sort-Object -Unique)) {
    Grant-Role $app.identity.principalId $resourceId 'a97b65f3-24c7-4388-baec-2e87135dc908'
}
Grant-Role $search.identity.principalId $sourceScope '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
Invoke-AzJson (@('functionapp', 'config', 'appsettings', 'set', '--subscription', $SubscriptionId.ToString(),
    '--resource-group', $ResourceGroup, '--name', $FunctionApp, '--settings') + $settings) | Out-Null
foreach ($policy in @('scm', 'ftp')) {
    Write-ArmJson "https://management.azure.com$appId/basicPublishingCredentialsPolicies/${policy}?api-version=2024-04-01" 'PUT' @{
        properties = @{ allow = $false }
    } | Out-Null
}
if ($PackagePath) {
    if (-not (Test-Path -LiteralPath $PackagePath -PathType Leaf)) { throw 'PackagePath must identify a ZIP file.' }
    if ($RbacPropagationSeconds) { Start-Sleep -Seconds $RbacPropagationSeconds }
    $scmHost = @($app.properties.enabledHostNames | Where-Object { $_ -like '*.scm.*' }) | Select-Object -First 1
    if (-not $scmHost) { throw 'No SCM hostname was returned; cannot perform Entra deployment.' }
    # az rest treats @file bodies as text; use an in-memory ARM token for binary ZIP.
    # Current CLI Flex config-zip uses this same bearer-only endpoint.
    $access = Invoke-AzJson @('account', 'get-access-token', '--subscription', $SubscriptionId.ToString(),
        '--resource', 'https://management.azure.com/')
    $headers = @{ Authorization = 'Bearer ' + $access.accessToken }
    try {
        $publish = Invoke-WebRequest -Method Post -Uri "https://$scmHost/api/publish?RemoteBuild=true&Deployer=keyless_sample" `
            -Headers $headers -ContentType 'application/zip' -InFile (Resolve-Path -LiteralPath $PackagePath).Path
        if ($publish.StatusCode -notin @(200, 202)) { throw 'OneDeploy did not accept the package.' }
        $deadline = [DateTime]::UtcNow.AddSeconds($DeploymentTimeoutSeconds)
        $succeeded = $false
        do {
            Start-Sleep -Seconds 5
            $poll = Invoke-WebRequest -Uri "https://$scmHost/api/deployments/latest" -Headers $headers -SkipHttpErrorCheck
            if ($poll.StatusCode -eq 404) { continue }
            if ($poll.StatusCode -notin @(200, 202)) { throw "OneDeploy status request failed (HTTP $($poll.StatusCode))." }
            $status = $poll.Content | ConvertFrom-Json
            if ($status.status -in @(-1, 3, 5, 6)) { throw "OneDeploy failed or was cancelled (status $($status.status))." }
            if ($status.status -eq 4) { $succeeded = $true; break }
        } while ([DateTime]::UtcNow -lt $deadline)
        if (-not $succeeded) { throw 'Timed out awaiting successful OneDeploy status. Inspect deployment logs.' }
    }
    finally { $headers.Clear(); $access = $null }
    Write-Host 'Verified successful Entra OneDeploy remote build.'
}
Write-Host 'Configured: Search MI -> source container; Function MI -> models; required EasyAuth; keyless host and deployment.'
Write-Host 'Next: create Search data source/skillset/index/indexer, run indexing, verify anonymous Function POST is 401 and query vectors work.'
