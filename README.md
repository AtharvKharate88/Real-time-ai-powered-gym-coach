# AI Gym Coach

A browser-first workout coach. MediaPipe Pose Lite runs on the athlete’s device; camera frames are not sent to a server. The production app is a static React/Vite site hosted on GitHub Pages. No backend, database, API key, account, or credit card is required to deploy and use the core workout flow.

## Free deployment in about five minutes

1. Create a **public** GitHub repository named `Real-time-ai-powered-gym-coach` (or use the repository you already have).
2. From the project root, commit and push the updated files to the `main` branch:

   ```powershell
   git add README.md .github frontend/.env.example frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/App.tsx frontend/src/components/CameraSetupPage.tsx frontend/src/components/DashboardPage.tsx frontend/src/components/LandingPage.tsx frontend/src/components/WorkoutPage.tsx frontend/src/services/api.ts frontend/src/workers frontend/public/models frontend/public/mediapipe
   git commit -m "Move pose tracking to the browser and deploy on Pages"
   git push origin main
   ```

3. On GitHub, open **Settings → Pages** and set **Build and deployment → Source** to **GitHub Actions**.
4. Open the repository’s **Actions** tab. The “Deploy AI Gym Coach to GitHub Pages” workflow builds and publishes the site. Wait for the green check.
5. Open **Settings → Pages** to follow the live link. For this repository it will be `https://atharvkharate88.github.io/Real-time-ai-powered-gym-coach/`.

The workflow uses GitHub’s hosted runner and Pages. A public repository and standard GitHub Pages use do not require a payment method. Hosting providers can change their terms, so no third-party host can be guaranteed free forever; this setup has no paid service dependency or trial clock today. HTTPS is provided by Pages, which is required for camera access.

## Local development

Requirements: Node.js 20 or newer and npm.

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the local URL printed by Vite. You do not need to create a `.env` file. The optional `frontend/.env.example` is intentionally empty of secrets.

## How it works

- `frontend/` contains the complete deployed app. GitHub Actions builds it to `frontend/dist`.
- `frontend/public/models/pose_landmarker_lite.task` and `frontend/public/mediapipe/wasm/` are served with the site, so inference has no third-party runtime dependency after deployment.
- The camera is requested at up to 640×480. Inference is scheduled at about 15 FPS, with one inference at a time; the browser uses the GPU delegate when available and falls back to CPU.
- Workout history and preferences are stored in that browser’s local storage. They do not sync to another device and can be cleared with browser data.
- Camera frames and pose landmarks remain in the browser. This avoids backend round trips and backend cold starts; frame speed still depends on the user’s device.
- The `backend/` directory is retained for the previous self-hosted API, persistence, and OAuth implementation. GitHub Pages does not run it, and it is not needed for the static client-side workout experience.

## Notes

The client-side counter uses pose landmarks and exercise-specific joint angle thresholds for squats, push-ups, curls, shoulder presses, and lunges. Treat feedback as an estimate, not medical advice. Browser/device and real-world movement validation remains important. The Lite model is smaller and faster than Full and is used to reduce initialization and per-frame cost.

If you fork this project under a differently named repository, update `base` in `frontend/vite.config.ts` to `/<your-repository-name>/` before deploying.
