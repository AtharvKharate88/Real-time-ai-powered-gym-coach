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

## Estimate assumptions

These are estimates, not measured Azure bills. The model assumes no other Container Apps use in the same subscription, one daily workout session of about one hour per cohort, 30-second checkpoints, scale-to-zero outside requests, and no video uploads or GPU inference. At 10 users this is about 36,000 API requests/month. At 30 users it is about 108,000 API requests/month. These are below Container Apps' published 2 million free monthly requests.

With one 0.5 vCPU / 1 GiB replica serving the sessions, 10-user use is approximately 58,500 vCPU-seconds and 117,000 GiB-seconds monthly. At 30 concurrent users, even a conservative three-replica hour for each cohort is approximately 175,500 vCPU-seconds and 351,000 GiB-seconds. Container Apps publishes monthly free grants of 180,000 vCPU-seconds and 360,000 GiB-seconds per subscription, so both illustrative scenarios are estimated at $0 Container Apps compute. The 30-user scenario is close to the free-grant edge; longer sessions, more scale-out, other apps using the same grant, or background jobs can consume Azure credit. Beyond grants, charges are deducted from student credit, and the subscription stops when the credit is exhausted.

Idle cost after scaling to zero is $0 for Container Apps compute. The app has no minimum replicas. Static files are included in the same app, so no Static Web Apps resource is needed. The GHCR package has no Azure charge. This estimate excludes existing Neon charges and optional third-party AI API usage. Keep the Groq API key unset for the pilot unless its separate billing terms are reviewed.

## Deployment order

1. Build and inspect the container image in GitHub Actions. The workflow is manual only.
2. If deploying from GHCR, review that this application image will be publicly downloadable, then set the package visibility to public. The repository is already public, and no secrets are baked into the image.
3. Sign in to Azure CLI and select the existing Azure for Students subscription. Confirm the portal still shows the student offer, remaining credit, and expiry. Never upgrade the subscription.
4. Create a new, dedicated resource group in Central India and deploy `main.bicep` to it. Pass the Neon pooled database URL, Google OAuth client ID/secret, and a new random session secret as secure parameters. Do not commit a parameter file containing credentials.
5. Add the Bicep output `googleOAuthCallbackUrl` to the existing Google OAuth client's authorized redirect URIs. This must be done before completing Google sign-in in the deployed app.
6. Test HTTPS, `/api/health`, Google sign-in, a saved workout, and a recovery checkpoint. Verify the app scales to zero after use and inspect actual Azure credit consumption.

No resource is created by the files in this folder. The subscription and credit checks above were read-only.
