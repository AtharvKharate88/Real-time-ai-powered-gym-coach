# Azure student-credit deployment

The deployment uses one Azure Container App to serve both the Vite frontend and FastAPI API from the same HTTPS origin. This keeps the existing secure, HTTP-only login cookie first-party in desktop Chrome, Android browsers, and iPhone Safari. Workout pose detection remains on the user's device.

## Cost controls

- Use the Azure for Students subscription only. Do not upgrade it to Pay-As-You-Go.
- Use a Consumption-only Container Apps environment, `minReplicas: 0`, `maxReplicas: 3`, and a 0.5 vCPU / 1 GiB container.
- Disable retained Azure logs (`destination: none`). Live log streaming remains available while replicas run.
- Do not create an ACR, GPU, dedicated workload profile, NAT Gateway, or paid monitoring workspace.
- The image is built in GitHub Actions and stored in GHCR. The package must be public for Azure's anonymous image pull, so review the public exposure before changing package visibility.
- Neon remains external. Its own plan and quota are not covered by Azure student credit.

Azure for Students currently has a hard credit stop: Microsoft says services and the subscription are disabled when the credit is used or expires, and continuing requires a support-mediated upgrade. Do not accept or initiate an upgrade. This is the safeguard that prevents Azure usage from turning into automatic Pay-As-You-Go charges.

## Current deployment

- Resource group: `rg-ai-gym-coach-student`
- Azure region: UAE North. The Student subscription's region policy excludes Central India, and the `Microsoft.App` resource provider does not offer India South Central.
- Container Apps environment: Consumption, logs disabled.
- Container App: `ai-gym-coach-atharv-2211`, minimum 0 / maximum 3 replicas, HTTP scale threshold 10 concurrent requests per replica.
- Application URL: <https://ai-gym-coach-atharv-2211.happyocean-b30f4c05.uaenorth.azurecontainerapps.io>
- Google callback URI to add in Google Cloud OAuth settings: <https://ai-gym-coach-atharv-2211.happyocean-b30f4c05.uaenorth.azurecontainerapps.io/api/auth/google/callback>

The deployed frontend, API, and Neon health endpoints returned HTTP 200. A 30-way read-only Neon health check returned 30/30 HTTP 200. This is a smoke check, not a sustained workout load test. Google sign-in requires the callback URI above to be added to the existing Google OAuth client.

## Estimate assumptions

These are estimates, not measured Azure bills. The model assumes no other Container Apps use in the same subscription, one daily workout session of about one hour per cohort, 30-second checkpoints, scale-to-zero outside requests, and no video uploads or GPU inference. At 10 users this is about 36,000 API requests/month. At 30 users it is about 108,000 API requests/month. These are below Container Apps' published 2 million free monthly requests.

With one 0.5 vCPU / 1 GiB replica serving the sessions, 10-user use is approximately 58,500 vCPU-seconds and 117,000 GiB-seconds monthly. At 30 concurrent users, even a conservative three-replica hour for each cohort is approximately 175,500 vCPU-seconds and 351,000 GiB-seconds. Container Apps publishes monthly free grants of 180,000 vCPU-seconds and 360,000 GiB-seconds per subscription, so both illustrative scenarios are estimated at $0 Container Apps compute. The 30-user scenario is close to the free-grant edge; longer sessions, more scale-out, other apps using the same grant, or background jobs can consume Azure credit. Beyond grants, charges are deducted from student credit, and the subscription stops when the credit is exhausted.

Idle cost after scaling to zero is $0 for Container Apps compute. The app has no minimum replicas. Static files are included in the same app, so no Static Web Apps resource is needed. The GHCR package has no Azure charge. This estimate excludes existing Neon charges and optional third-party AI API usage. Keep the Groq API key unset for the pilot unless its separate billing terms are reviewed.

## Deployment order

1. The public GHCR image has been published. The GitHub Actions workflow rebuilds it on frontend/backend source changes; the package contains no credentials.
2. Sign in to Azure CLI and select the existing Azure for Students subscription. Confirm the Student offer is still active. Never upgrade it to Pay-As-You-Go.
3. For a new environment, create a Consumption environment in an allowed region with `az containerapp env create --name <appName>-env --resource-group <resourceGroup> --location uaenorth --logs-destination none`. Then deploy `main.bicep` to the dedicated resource group, passing the frontend origin, Google callback URL, Neon pooled database URL, Google OAuth client ID/secret, and a new random session secret. Mark database and OAuth secrets as secure; never commit a parameter file containing credentials.
4. Add the Google callback URI to the existing Google OAuth client's authorized redirect URIs before completing Google sign-in.
5. Test a Google sign-in, a saved workout, and a recovery checkpoint. Check idle scale-to-zero and review actual Azure credit consumption after usage has posted.
