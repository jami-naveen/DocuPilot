@description('Region for all resources')
param location string = resourceGroup().location

@description('Base name prefix for resources')
param baseName string

@description('Container registry login server (e.g., <name>.azurecr.io)')
param containerRegistryServer string

@description('Backend container image tag (e.g., <registry>/rag-api:latest)')
param backendImage string

@description('Frontend container image tag (e.g., <registry>/rag-web:latest)')
param frontendImage string

@description('Azure OpenAI SKU')
@allowed([ 'S0' 'S1' ])
param openAiSku string = 'S0'

@description('Azure AI Search SKU')
@allowed([ 'basic' 'standard' 'standard2' ])
param searchSku string = 'basic'

@description('Storage account SKU')
@allowed([ 'Standard_LRS' 'Standard_GRS' ])
param storageSku string = 'Standard_LRS'

var storageName = toLower('${baseName}data')
var searchName = toLower('${baseName}search')
var openAiName = toLower('${baseName}aoai')
var containerEnvName = '${baseName}-env'
var identityName = '${baseName}-capp-id'
var rawContainer = 'raw-documents'
var processedContainer = 'processed-documents'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: storageSku
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: '${storage.name}/default'
  properties: {
    cors: {
      corsRules: []
    }
  }
}

resource rawContainerResource 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storage.name}/default/${rawContainer}'
  properties: {
    publicAccess: 'None'
  }
}

resource processedContainerResource 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: '${storage.name}/default/${processedContainer}'
  properties: {
    publicAccess: 'None'
  }
}

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  sku: {
    name: searchSku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
}

resource openAi 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: openAiSku
    tier: 'Standard'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: []
      registries: [
        {
          server: containerRegistryServer
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
      }
      dapr: null
    }
    template: {
      containers: [
        {
          name: 'api'
          image: backendImage
          env: [
            {
              name: 'AZURE_STORAGE_ACCOUNT_URL'
              value: 'https://${storage.name}.blob.core.windows.net'
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: 'https://${searchService.name}.search.windows.net'
            }
            {
              name: 'AZURE_SEARCH_INDEX'
              value: 'rag-index'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: 'https://${openAi.name}.openai.azure.com'
            }
            {
              name: 'AZURE_STORAGE_RAW_CONTAINER'
              value: rawContainer
            }
            {
              name: 'AZURE_STORAGE_PROCESSED_CONTAINER'
              value: processedContainer
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-web'
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: containerRegistryServer
        }
      ]
      ingress: {
        external: true
        targetPort: 80
      }
    }
    template: {
      containers: [
        {
          name: 'web'
          image: frontendImage
          env: [
            {
              name: 'VITE_API_BASE_URL'
              value: backendApp.properties.configuration.ingress?.fqdn ?? ''
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, managedIdentity.id, 'storage-blob-data-contributor')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, managedIdentity.id, 'search-data-contributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4200-8fbd-beebf4aa0f89')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output storageAccountName string = storage.name
output searchServiceName string = searchService.name
output openAiAccountName string = openAi.name
output backendAppUrl string = backendApp.properties.configuration.ingress?.fqdn
output frontendAppUrl string = frontendApp.properties.configuration.ingress?.fqdn
