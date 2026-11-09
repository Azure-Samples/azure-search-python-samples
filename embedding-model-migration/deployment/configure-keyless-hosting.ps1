#requires -Version 7.2
<#
.SYNOPSIS
Convert an existing Python Flex Consumption app's host and deployment storage to MI.
.DESCRIPTION
Requires az login and permission to update the app and assign storage roles.
No storage keys are retrieved. Existing runtime/scale/network configuration is preserved.
HTTP-only sample: Blob Data Owner is required by the host; Table Data Contributor
allows host diagnostics. Queue roles are unnecessary without queue/blob triggers.
Does NOT disable Shared Key on existing accounts (other applications may use them).
APPLICATIONINSIGHTS_CONNECTION_STRING identifies a telemetry destination, not a
credential. With -ApplicationInsightsResourceId, telemetry uses Entra authentication.
Do not run concurrent configuration writers while converting the app.
References:
https://learn.microsoft.com/azure/azure-functions/manage-connections?pivots=functions-auth-identity&tabs=host
https://learn.microsoft.com/azure/azure-functions/flex-consumption-how-to#configure-deployment-settings
.EXAMPLE
.\configure-keyless-hosting.ps1 -SubscriptionId '<subscription-guid>' `
  -ResourceGroup '<rg>' -FunctionApp '<app>' `
  -HostStorageResourceId '/subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<account>'
.EXAMPLE
.\configure-keyless-hosting.ps1 -ResourceGroup example -FunctionApp example `
  -HostStorageResourceId '/subscriptions/example/resourceGroups/example/providers/Microsoft.Storage/storageAccounts/example' -PrintConfiguration
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$FunctionApp,
    [Parameter(Mandatory)][string]$HostStorageResourceId,
    [guid]$SubscriptionId,
    [string]$ApplicationInsightsResourceId,
    [ValidateRange(0, 900)][int]$RbacPropagationSeconds = 120,
    [switch]$PrintConfiguration
)
$ErrorActionPreference = 'Stop'
$roles = @{
    BlobOwner = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
    BlobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    TableContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
    MetricsPublisher = '3913510d-42f4-4e42-8a64-420c390055eb'
}
if ($HostStorageResourceId -notmatch '^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft.Storage/storageAccounts/([^/]+)$') {
    throw 'HostStorageResourceId must be a storage account resource ID.'
}
$hostAccountName = $Matches[1]
if ($PrintConfiguration) {
    @{
        hostSettings = @{
            AzureWebJobsStorage__accountName = $hostAccountName
            AzureWebJobsStorage__credential = 'managedidentity'
        }
        removeSettings = @('AzureWebJobsStorage', 'AzureWebJobsStorage__clientId',
            'AzureWebJobsStorage__managedIdentityResourceId', 'AZURE_CLIENT_ID',
            'DEPLOYMENT_STORAGE_CONNECTION_STRING')
        functionAppConfigMerge = @{
            runtime = @{ name = 'python'; version = '<preserve existing supported version>' }
            deployment = @{ storage = @{
                type = 'blobContainer'; value = '<preserve existing container URL>'
                authentication = @{ type = 'SystemAssignedIdentity' }
            } }
        }
        preserve = 'Read and copy the ENTIRE existing functionAppConfig; replace only deployment.storage.authentication.'
        roleAssignments = @(
            @{ scope = $HostStorageResourceId; role = 'Storage Blob Data Owner' }
            @{ scope = $HostStorageResourceId; role = 'Storage Table Data Contributor' }
            @{ scope = '<existing deployment storage account>'; role = 'Storage Blob Data Contributor (if separate from host)' }
        )
        monitoring = 'Optional: Monitoring Metrics Publisher on supplied App Insights + APPLICATIONINSIGHTS_AUTHENTICATION_STRING=Authorization=AAD'
        sharedResourceChanges = 'Never disables account Shared Key or App Insights local auth on existing resources.'
    } | ConvertTo-Json -Depth 15
    return
}
function Invoke-AzJson([string[]]$Arguments) {
    $result = & az @Arguments --only-show-errors --output json 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI operation failed ($($Arguments[0])); no credentials or app settings are logged." }
    if ($result) { ($result -join "`n") | ConvertFrom-Json -AsHashtable }
}
function Write-ArmJson([string]$Url, [string]$Method, $Body) {
    $path = Join-Path $PSScriptRoot ('.hosting-payload-' + [guid]::NewGuid() + '.json')
    try {
        [IO.File]::WriteAllText($path, ($Body | ConvertTo-Json -Depth 50), [Text.UTF8Encoding]::new($false))
        Invoke-AzJson @('rest', '--method', $Method, '--url', $Url, '--body', "@$path")
    }
    finally { if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force } }
}
function Grant-Role([string]$Principal, [string]$Scope, [string]$Role) {
    $existing = @(Invoke-AzJson @('role', 'assignment', 'list', '--assignee-object-id', $Principal,
        '--scope', $Scope, '--query', "[?roleDefinitionId!=null]"))
    if (-not ($existing | Where-Object { $_.scope -ieq $Scope -and $_.roleDefinitionId.EndsWith("/$Role") })) {
        Invoke-AzJson @('role', 'assignment', 'create', '--assignee-object-id', $Principal,
            '--assignee-principal-type', 'ServicePrincipal', '--scope', $Scope, '--role', $Role) | Out-Null
    }
}
if (-not $SubscriptionId -or $SubscriptionId -eq [guid]::Empty) {
    $SubscriptionId = [guid](Invoke-AzJson @('account', 'show')).id
}
$appId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$FunctionApp"
$appUrl = "https://management.azure.com${appId}?api-version=2024-04-01"
$app = Invoke-AzJson @('rest', '--method', 'GET', '--url', $appUrl)
$plan = Invoke-AzJson @('rest', '--method', 'GET', '--url',
    "https://management.azure.com$($app.properties.serverFarmId)?api-version=2024-04-01")
if ($plan.sku.name -ne 'FC1') { throw 'Only Flex Consumption (FC1) is supported.' }
$config = $app.properties.functionAppConfig
if (-not $config -or $config.runtime.name -ne 'python' -or
    $config.deployment.storage.type -ne 'blobContainer') {
    throw 'Expected an existing Python Flex runtime and deployment blobContainer; no configuration changed.'
}
$deploymentUri = [uri]$config.deployment.storage.value
if ($deploymentUri.Scheme -ne 'https' -or $deploymentUri.Query -or
    $deploymentUri.Host -notmatch '^([a-z0-9]+)\.blob\.core\.windows\.net$') {
    throw 'This sample supports credential-free public Azure deployment storage URLs only.'
}
$deploymentAccountName = $Matches[1]
$deploymentAccounts = @(Invoke-AzJson @('storage', 'account', 'list', '--subscription',
    $SubscriptionId.ToString(), '--query', "[?name=='$deploymentAccountName'].id"))
if ($deploymentAccounts.Count -ne 1) { throw 'Deployment account must exist in the selected subscription.' }
$deploymentAccountId = $deploymentAccounts[0]
$hostStorage = Invoke-AzJson @('rest', '--method', 'GET', '--url',
    "https://management.azure.com${HostStorageResourceId}?api-version=2023-05-01")
if ($hostStorage.properties.primaryEndpoints.blob -ne "https://$hostAccountName.blob.core.windows.net/") {
    throw 'This sample requires standard public Azure storage endpoints.'
}
if (-not $app.identity.principalId) {
    $identity = if ($app.identity) { $app.identity } else { @{} }
    $identity.type = if ($identity.userAssignedIdentities.Count) { 'SystemAssigned, UserAssigned' } else { 'SystemAssigned' }
    Write-ArmJson $appUrl 'PATCH' @{ identity = $identity } | Out-Null
    $app = Invoke-AzJson @('rest', '--method', 'GET', '--url', $appUrl)
}
$principal = $app.identity.principalId
Grant-Role $principal $HostStorageResourceId $roles.BlobOwner
Grant-Role $principal $HostStorageResourceId $roles.TableContributor
if ($deploymentAccountId -ine $HostStorageResourceId) {
    Grant-Role $principal $deploymentAccountId $roles.BlobContributor
}
if ($ApplicationInsightsResourceId) {
    $insights = Invoke-AzJson @('rest', '--method', 'GET', '--url',
        "https://management.azure.com${ApplicationInsightsResourceId}?api-version=2020-02-02")
    if (-not $insights.properties.ConnectionString) { throw 'Application Insights resource has no telemetry connection string.' }
    Grant-Role $principal $ApplicationInsightsResourceId $roles.MetricsPublisher
}
if ($RbacPropagationSeconds) { Start-Sleep -Seconds $RbacPropagationSeconds }
# Refresh immediately before PATCH: functionAppConfig is replaced as a whole.
$app = Invoke-AzJson @('rest', '--method', 'GET', '--url', $appUrl)
$config = $app.properties.functionAppConfig
$oldConnectionSetting = $config.deployment.storage.authentication.storageAccountConnectionStringName
$config.deployment.storage.authentication = @{ type = 'SystemAssignedIdentity' }
Write-ArmJson $appUrl 'PATCH' @{ properties = @{ functionAppConfig = $config; httpsOnly = $true } } | Out-Null
$settings = @("AzureWebJobsStorage__accountName=$hostAccountName", 'AzureWebJobsStorage__credential=managedidentity')
if ($ApplicationInsightsResourceId) {
    $settings += 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING=Authorization=AAD'
    $settings += "APPLICATIONINSIGHTS_CONNECTION_STRING=$($insights.properties.ConnectionString)"
}
Invoke-AzJson (@('functionapp', 'config', 'appsettings', 'set', '--subscription', $SubscriptionId.ToString(),
    '--resource-group', $ResourceGroup, '--name', $FunctionApp, '--settings') + $settings) | Out-Null
$remove = @('AzureWebJobsStorage', 'AzureWebJobsStorage__clientId', 'AzureWebJobsStorage__managedIdentityResourceId',
    'AzureWebJobsStorage__blobServiceUri', 'AzureWebJobsStorage__queueServiceUri', 'AzureWebJobsStorage__tableServiceUri',
    'AZURE_CLIENT_ID', 'DEPLOYMENT_STORAGE_CONNECTION_STRING')
if ($oldConnectionSetting) {
    if ($oldConnectionSetting -eq 'APPLICATIONINSIGHTS_CONNECTION_STRING') {
        throw 'Unexpected deployment connection setting; inspect manually before removing settings.'
    }
    $remove += $oldConnectionSetting
}
Invoke-AzJson (@('functionapp', 'config', 'appsettings', 'delete', '--subscription', $SubscriptionId.ToString(),
    '--resource-group', $ResourceGroup, '--name', $FunctionApp, '--setting-names') + @($remove | Sort-Object -Unique)) | Out-Null
$actual = Invoke-AzJson @('rest', '--method', 'GET', '--url', $appUrl)
$actualSettings = @(Invoke-AzJson @('functionapp', 'config', 'appsettings', 'list', '--subscription',
    $SubscriptionId.ToString(), '--resource-group', $ResourceGroup, '--name', $FunctionApp))
$map = @{}
foreach ($setting in $actualSettings) { $map[$setting.name] = $setting.value }
if ($actual.properties.functionAppConfig.deployment.storage.authentication.type -ne 'SystemAssignedIdentity' -or
    $map.AzureWebJobsStorage__accountName -ne $hostAccountName -or
    $map.AzureWebJobsStorage__credential -ne 'managedidentity' -or
    @($remove | Where-Object { $map.ContainsKey($_) }).Count) {
    throw 'Keyless hosting verification failed; inspect configuration without printing app-setting values.'
}
Write-Host 'Verified: system-assigned MI for host storage and deployment storage; inherited connection settings removed.'
Write-Host 'RBAC can take up to 10 minutes to propagate. Runtime startup and deployment must still be tested.'
