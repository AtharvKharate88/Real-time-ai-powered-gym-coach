targetScope = 'resourceGroup'

@description('Azure region for the serverless application resources.')
param location string = 'centralindia'

@description('Globally unique lower-case Container App name, 2-32 characters.')
param appName string = 'ai-gym-coach-atharv'

@description('Public GHCR image. The package must be public for anonymous pulls.')
param backendImage string = 'ghcr.io/atharvkharate88/ai-gym-coach:azure'

@secure()
@description('Pooled Neon PostgreSQL connection string used by the API.')
param databaseUrl string

@description('Google OAuth client ID. Add the resulting ACA callback URL to the Google OAuth client.')
param googleClientId string

@secure()
@description('Google OAuth client secret.')
param googleClientSecret string

@secure()
@description('Unique random signing secret, at least 32 characters.')
param sessionSecret string

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'none'
    }
    zoneRedundant: false
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        { name: 'database-url', value: databaseUrl }
        { name: 'google-client-secret', value: googleClientSecret }
        { name: 'session-secret', value: sessionSecret }
      ]
    }
    template: {
      containers: [
        {
          name: 'ai-gym-coach'
          image: backendImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'ENVIRONMENT', value: 'production' }
            { name: 'COOKIE_SECURE', value: 'true' }
            { name: 'AUTH_COOKIE_SAMESITE', value: 'lax' }
            { name: 'LOG_LEVEL', value: 'INFO' }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'GOOGLE_CLIENT_ID', value: googleClientId }
            { name: 'GOOGLE_CLIENT_SECRET', secretRef: 'google-client-secret' }
            { name: 'SESSION_SECRET', secretRef: 'session-secret' }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/api/health', port: 8000, scheme: 'HTTP' }
              periodSeconds: 10
              failureThreshold: 30
            }
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000, scheme: 'HTTP' }
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

output applicationUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
output googleOAuthCallbackUrl string = 'https://${app.properties.configuration.ingress.fqdn}/api/auth/google/callback'
