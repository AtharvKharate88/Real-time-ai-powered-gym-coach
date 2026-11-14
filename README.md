# AI Gym Coach

AI Gym Coach uses React, FastAPI, WebRTC, MediaPipe Pose, and Neon PostgreSQL. The browser captures one webcam stream and sends it to the authenticated FastAPI service over WebRTC. FastAPI processes frames, draws the pose overlay, tracks reps and form, and returns the processed video. Workout sessions and history belong to the signed-in user.

## Architecture

```text
Browser camera (640×480, ideal 15 FPS, max 24)
  → WebRTC video track
  → FastAPI /api/webrtc/offer
  → MediaPipe Pose + exercise detectors
  → processed video track back to browser
  → workout metrics / voice / stop APIs
  → Neon PostgreSQL workout history
```

Inference is performed on the backend with the Full Pose Landmarker model. Frame processing uses a one-frame queue and replaces stale frames so slow inference does not create a growing backlog. Voice generation runs outside the video inference loop. The frontend keeps one camera stream and one peer connection for a workout.

The React application retains Google sign-in, user-specific dashboard and history, progress views, manual workout entry, and workout controls. The backend includes user ownership checks, SQLAlchemy persistence, and Alembic migrations. Camera video is sent to the configured backend for processing.

## Configuration

Keep credentials in local environment files or the backend host’s environment settings. Do not put database or OAuth secrets in frontend `VITE_*` variables.

Backend variables are documented in `backend/.env.example`. `DATABASE_URL` is the Neon pooled application connection; `DIRECT_DATABASE_URL` is the direct connection used by Alembic. Google OAuth requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and `SESSION_SECRET`. Set `FRONTEND_ORIGIN` to the exact deployed frontend origin. For cross-site HTTPS deployments, configure secure cookies and `AUTH_COOKIE_SAMESITE=none`.

The frontend uses `VITE_API_BASE_URL` to reach FastAPI. The local `frontend/.env.example` points to `http://localhost:8000`. For GitHub Pages, configure the repository variable `VITE_API_BASE_URL` to the HTTPS backend origin; the Actions build fails if it is missing. Set backend `FRONTEND_REDIRECT_URL` to the full Pages URL including its repository path so OAuth returns to the app. For Vercel, set `VITE_API_BASE_URL` in the project’s build environment; `FRONTEND_REDIRECT_URL` can be omitted because the frontend is at the origin root. The Pages build uses the repository subpath, while Vercel uses `/`.

## Run locally

Requirements: Node.js 20+, Python 3.12, a webcam, and backend environment values for OAuth/database use.

Start FastAPI from `backend`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal, start Vite:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the Vite URL. The camera is requested on the camera setup page and that same stream is handed to the workout view. Browsers require HTTPS or localhost for camera access.

## Database migrations

Run migrations only when intentionally updating the configured database schema:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
```

Alembic uses `DIRECT_DATABASE_URL`. Do not run migrations against production without reviewing the migration first.

## Tests and build

From the repository root:

```powershell
npm --prefix frontend run build
python -m unittest discover -s backend/tests -v
```

The Neon integration test is opt-in with `AI_GYM_NEON_TESTS=1` and writes temporary test rows before deleting them. Use a development database only. Detector tests use synthetic landmark sequences; they do not replace real camera and movement checks.

## Deployment

GitHub Pages publishes the frontend through `.github/workflows/pages.yml`. Configure the repository variable `VITE_API_BASE_URL` before deployment. Deploy the API separately using `render.yaml` or another FastAPI host, configure its environment variables, and set its `FRONTEND_ORIGIN` to the Pages site origin. Add the backend callback URL to the Google OAuth client’s authorized redirect URIs. For Vercel, use `frontend` as the project root and set `VITE_API_BASE_URL` to the backend HTTPS origin.

The backend’s `/api/health` and `/api/health/database` endpoints report service and database health. Live camera testing requires a browser with camera permission and a reachable HTTPS backend that supports WebRTC.

Treat exercise feedback and form scores as estimates, not medical advice.
