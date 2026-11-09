<#
.SYNOPSIS
Require keyless, single-tenant Entra authentication on an existing Function app.
.DESCRIPTION
Run BEFORE publishing function code. Requires Azure CLI sign-in, permission to
update the Function app, and (with -EnableLocalCliAccess) ownership/permission to
update the existing API app registration. No client secret is created or used.
The existing API registration must expose api://<ApiApplicationClientId>.
SearchIdentityObjectId is the Search service's system-assigned principalId,
not its clientId. Only that identity and explicitly supplied test users can call.
Optional CLI preauthorization exposes access_as_user and trusts the Microsoft
Azure CLI public client for that delegated permission. Tenant policies may still
require administrator consent; verify live token acquisition rather than bypassing
policy. This script does not change Foundry RBAC or deploy function code.
.EXAMPLE
.\configure-entra-auth.ps1 -ResourceGroup '<resource-group>' -FunctionApp '<function-app>' `
  -TenantId '<tenant-guid>' -ApiApplicationClientId '<api-app-client-guid>' `
  -SearchIdentityObjectId '<search-principal-guid>' -TestUserObjectIds '<user-guid>' `
  -EnableLocalCliAccess
.EXAMPLE
.\configure-entra-auth.ps1 -ResourceGroup '<resource-group>' -FunctionApp '<function-app>' `
  -TenantId '<tenant-guid>' -ApiApplicationClientId '<api-app-client-guid>' `
  -SearchIdentityObjectId '<search-principal-guid>' -PrintConfiguration
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$FunctionApp,
    [Parameter(Mandatory)][guid]$TenantId,
    [Parameter(Mandatory)][guid]$ApiApplicationClientId,
    [Parameter(Mandatory)][guid]$SearchIdentityObjectId,
    [guid[]]$TestUserObjectIds = @(),
    [guid]$SubscriptionId,
    [switch]$EnableLocalCliAccess,
    [switch]$PrintConfiguration
)
$ErrorActionPreference = 'Stop'
$audience = "api://$ApiApplicationClientId"
$principals = @(@($SearchIdentityObjectId) + @($TestUserObjectIds) |
    ForEach-Object { $_.ToString() } | Sort-Object -Unique)
$configuration = @{
    properties = @{
        platform = @{ enabled = $true }
        globalValidation = @{
            requireAuthentication = $true
            unauthenticatedClientAction = 'Return401'
            excludedPaths = @()
        }
        identityProviders = @{
            azureActiveDirectory = @{
                enabled = $true
                registration = @{
                    clientId = $ApiApplicationClientId.ToString()
                    openIdIssuer = "https://login.microsoftonline.com/$TenantId/v2.0"
                }
                validation = @{
                    allowedAudiences = @($audience)
                    defaultAuthorizationPolicy = @{
                        allowedPrincipals = @{ identities = $principals }
                    }
                }
            }
        }
        httpSettings = @{ requireHttps = $true }
    }
}
if ($PrintConfiguration) {
    $configuration | ConvertTo-Json -Depth 20
    return
}

function Invoke-AzJson([string[]]$Arguments) {
    $output = & az @Arguments --only-show-errors --output json 2>&1
    if ($LASTEXITCODE -ne 0) {
        $urlIndex = [Array]::IndexOf($Arguments, '--url')
        if ($Arguments[0] -eq 'rest' -and $urlIndex -ge 0 -and
            $Arguments[$urlIndex + 1] -like 'https://graph.microsoft.com/v1.0/applications/*') {
            # Only app-definition errors: never echo general command output,
            # which might include app settings or authentication credentials.
            $diagnostic = $output -join "`n"
            $diagnostic = $diagnostic -replace '(?i)Bearer\s+\S+', 'Bearer [REDACTED]'
            $diagnostic = $diagnostic -replace 'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED JWT]'
            $diagnostic = $diagnostic -replace '(?i)("?(?:access_token|refresh_token|id_token|client_secret|password|api[-_]?key|x-functions-key|authorization|connectionstring|sig)"?\s*[:=]\s*)("[^"]*"|[^\s,;}]+)', '$1[REDACTED]'
            if ($diagnostic.Length -gt 2000) { $diagnostic = $diagnostic.Substring(0, 2000) }
            throw "Azure Graph application request failed: $diagnostic"
        }
        throw "Azure CLI failed ($($Arguments[0])); inspect Azure permissions and tenant policy."
    }
    ($output -join "`n") | ConvertFrom-Json
}

function Write-AzureJson([string]$Url, [string]$Method, $Body) {
    # CLI @file avoids Windows native-command JSON quoting ambiguities.
    $path = Join-Path $PSScriptRoot ('.auth-payload-' + [guid]::NewGuid() + '.json')
    try {
        [IO.File]::WriteAllText($path, ($Body | ConvertTo-Json -Depth 30),
                              [Text.UTF8Encoding]::new($false))
        Invoke-AzJson @('rest', '--method', $Method, '--url', $Url, '--body', "@$path")
    }
    finally {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
}

$account = Invoke-AzJson @('account', 'show')
if ($account.tenantId -ne $TenantId.ToString()) {
    throw 'Azure CLI is signed into a different tenant; sign in to the specified tenant first.'
}
if (-not $SubscriptionId -or $SubscriptionId -eq [guid]::Empty) {
    $SubscriptionId = [guid]$account.id
}
$subscription = Invoke-AzJson @('account', 'show', '--subscription', $SubscriptionId.ToString())
if ($subscription.tenantId -ne $TenantId.ToString()) {
    throw 'The target subscription belongs to a different tenant.'
}
$application = Invoke-AzJson @('ad', 'app', 'show', '--id', $ApiApplicationClientId.ToString())
if ($application.signInAudience -ne 'AzureADMyOrg' -or
    $audience -notin @($application.identifierUris)) {
    throw 'The existing API registration must be single-tenant and expose the required api:// audience.'
}

if ($EnableLocalCliAccess) {
    $scopes = @($application.api.oauth2PermissionScopes | Where-Object { $null -ne $_ })
    $matches = @($scopes | Where-Object { $_.value -eq 'access_as_user' })
    if ($matches.Count -gt 1) { throw 'Duplicate access_as_user scopes are unsupported.' }
    if ($matches.Count -eq 1) {
        $scope = $matches[0]
        if (-not $scope.isEnabled) { throw 'The existing access_as_user scope is disabled.' }
    }
    else {
        $scope = @{
            id = [guid]::NewGuid().ToString()
            value = 'access_as_user'
            type = 'User'
            isEnabled = $true
            adminConsentDisplayName = 'Call the embedding Function as a signed-in user'
            adminConsentDescription = 'Call the embedding Function using delegated Entra authentication.'
            userConsentDisplayName = 'Call the embedding Function'
            userConsentDescription = 'Call the embedding Function on your behalf.'
        }
        $scopes += $scope
        $applicationUrl = "https://graph.microsoft.com/v1.0/applications/$($application.id)"
        # Graph must know the delegated scope before another request references
        # it in preAuthorizedApplications. Do not combine these two PATCHes.
        Write-AzureJson $applicationUrl 'PATCH' @{
            api = @{ oauth2PermissionScopes = $scopes }
        } | Out-Null
        $application = Invoke-AzJson @('rest', '--method', 'GET', '--url', $applicationUrl)
        if ($scope.id -notin @($application.api.oauth2PermissionScopes.id)) {
            throw 'The delegated scope did not persist; CLI preauthorization was not attempted. Retry later.'
        }
    }
    $cliClientId = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
    $preauthorized = @($application.api.preAuthorizedApplications |
        Where-Object { $_ -and $_.appId -ne $cliClientId })
    $existingCli = @($application.api.preAuthorizedApplications |
        Where-Object { $_.appId -eq $cliClientId })
    $permissions = @(@($existingCli | ForEach-Object { $_.delegatedPermissionIds }) +
        @($scope.id) | Sort-Object -Unique)
    $preauthorized += @{ appId = $cliClientId; delegatedPermissionIds = $permissions }
    $patch = @{ api = @{ preAuthorizedApplications = $preauthorized } }
    Write-AzureJson "https://graph.microsoft.com/v1.0/applications/$($application.id)" 'PATCH' $patch |
        Out-Null
}

$resource = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$FunctionApp"
$url = "https://management.azure.com$resource/config/authsettingsV2?api-version=2022-03-01"
Write-AzureJson $url 'PUT' $configuration | Out-Null
# Defense-in-depth application guard; this setting does not replace EasyAuth.
Invoke-AzJson @('functionapp', 'config', 'appsettings', 'set', '--subscription',
    $SubscriptionId.ToString(), '--resource-group', $ResourceGroup, '--name', $FunctionApp,
    '--settings', 'REQUIRE_ENTRA_AUTH=true') | Out-Null
$actual = (Invoke-AzJson @('rest', '--method', 'GET', '--url', $url)).properties
$aad = $actual.identityProviders.azureActiveDirectory
if (-not $actual.platform.enabled -or -not $actual.globalValidation.requireAuthentication -or
    $actual.globalValidation.unauthenticatedClientAction -ne 'Return401' -or
    @($actual.globalValidation.excludedPaths).Count -ne 0 -or -not $aad.enabled -or
    $aad.registration.clientId -ne $ApiApplicationClientId.ToString() -or
    @($aad.validation.allowedAudiences).Count -ne 1 -or
    $aad.validation.allowedAudiences[0] -ne $audience -or
    (Compare-Object $principals @($aad.validation.defaultAuthorizationPolicy.allowedPrincipals.identities))) {
    throw 'Required EasyAuth configuration did not persist; do not deploy function code.'
}
Write-Host "Verified required Entra EasyAuth: $audience"
Write-Host 'Next: publish the Function, verify anonymous POST returns 401, then test Search MI access.'
if ($EnableLocalCliAccess) {
    Write-Host "Verify local token acquisition: az account get-access-token --resource $audience --query expiresOn -o tsv"
    Write-Host 'Token acquisition and live embedding authorization have NOT been verified by this script.'
}
