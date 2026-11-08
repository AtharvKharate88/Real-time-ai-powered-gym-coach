# AI Gym Coach

AI Gym Coach is a React and FastAPI application for camera-based workouts. It uses MediaPipe Pose to track five supported exercises, reports detector-based form cues, and saves completed sessions to Neon PostgreSQL for signed-in users.

## Current features

- Google OAuth sign-in with an HttpOnly session cookie.
- User-specific workout history and ownership checks.
- Dashboard totals, recent sessions, and weekly activity from saved history.
- Monthly training calendar with green workout days, date selection, and per-day session details.
- Manual workout entry saved to the same signed-in account history.
- Exercise selection and camera preview before entering a workout.
- WebRTC processed video with a MediaPipe skeleton overlay.
- Rep and set counters, pause/resume/stop controls, and voice coaching when configured.
- Structured form feedback for squats, push-ups, dumbbell curls, shoulder press, and lunges.
- Estimated form score saved with new workout sessions when enough valid detector frames are available.
- A rep breakdown by configured set target for new camera-tracked sessions; it is calculated from total reps and target reps per set. Older and manually entered entries show totals because they do not include set-level counts.
- Neon PostgreSQL persistence managed with Alembic.

The form score averages valid detector frames: a frame with no tracked issue contributes 100, a warning contributes 75, and incorrect form contributes 50. At least 30 valid frames are required. This is an estimated coaching score, not a medical assessment. Older history entries have no score.

## Architecture

```text
frontend/  React + TypeScript + Vite
backend/   FastAPI + WebRTC + MediaPipe + SQLAlchemy + Alembic
Neon      PostgreSQL for users and saved workout history
```

The frontend calls FastAPI at `VITE_API_BASE_URL`. FastAPI uses the pooled Neon `DATABASE_URL`; Alembic uses the direct `DIRECT_DATABASE_URL`. Live video and active workout sessions are held in memory by the backend. Completed workout history is persisted in PostgreSQL.

### Main folders

- `frontend/src/components/` — landing page, dashboard, exercise selection, camera setup, and workout screen.
- `frontend/src/services/api.ts` — typed frontend API client.
- `backend/api/` — FastAPI routes, schemas, authentication, and session lifecycle.
- `backend/detectors/` — exercise-specific movement detectors.
- `backend/services/vision/` — MediaPipe processing, WebRTC frame work, and form scoring.
- `backend/models/` and `backend/database/` — SQLAlchemy models, engine, and repositories.
- `backend/migrations/versions/` — Alembic schema revisions.
- `backend/tests/` — unit, API, detector, and opt-in Neon integration tests.

## Requirements

- Windows PowerShell examples below; equivalent commands work on other operating systems.
- Python 3.12 is recommended for the pinned MediaPipe version.
- Node.js 18 or newer and npm.
- A Neon PostgreSQL database.
- Google OAuth web application credentials for sign-in.
- Optional: Groq API key for generated voice coaching.
- A webcam and a browser that supports WebRTC for live workouts.

## Configure the backend

From the repository root:

```powershell
Set-Location backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env`. Required values for normal API/database operation:

```dotenv
DATABASE_URL=postgresql+psycopg://ROLE:PASSWORD@YOUR-POOLER-HOST/DATABASE?sslmode=require
DIRECT_DATABASE_URL=postgresql+psycopg://ROLE:PASSWORD@YOUR-DIRECT-HOST/DATABASE?sslmode=require
FRONTEND_ORIGIN=http://localhost:5173
```

Use Neon’s **pooled** endpoint for `DATABASE_URL` (the host includes `-pooler`) and its **direct** endpoint for `DIRECT_DATABASE_URL` (the host does not include `-pooler`). Both URLs must use `postgresql+psycopg` and TLS. Never commit the real connection strings.

### Google OAuth

Set these backend variables:

```dotenv
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
SESSION_SECRET=your_random_secret_at_least_32_characters
AUTH_COOKIE_NAME=ai_gym_session
COOKIE_SECURE=false
```

Generate a session secret locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

In Google Cloud Console, create an OAuth client of type **Web application** and add the exact callback above under **Authorized redirect URIs**. The scheme, host, port, and path must match `GOOGLE_REDIRECT_URI`. For a deployed HTTPS app, set the production backend callback URL and `COOKIE_SECURE=true`. Set `FRONTEND_ORIGIN` to the frontend’s exact origin, including scheme and port, with no path.

### Optional voice and WebRTC configuration

Set `GROQ_API_KEY` to enable generated coaching cues. Without it, workouts and detector feedback remain available, but the UI reports voice coaching as unavailable. The backend uses Google’s public STUN server by default. If your network cannot establish WebRTC connections, configure `STUN_URL` or a TURN service using `TURN_URL`, `TURN_USERNAME`, and `TURN_CREDENTIAL`. Keep TURN credentials private.

## Configure the frontend

In a second PowerShell window, from the repository root:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm install
```

The local `frontend/.env` should contain:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Restart Vite after changing frontend environment variables.

## Database migrations

Run from the repository root:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
```

Alembic reads `backend/.env` and requires `DIRECT_DATABASE_URL`. Do not use the pooled URL for migrations. To check whether model metadata differs from the applied database schema:

```powershell
Set-Location backend
python -m alembic -c alembic.ini check
Set-Location ..
```

For transferring the retained legacy SQLite data, follow [MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md). The application uses PostgreSQL; the SQLite file is only read by the one-time transfer utility.

## Run locally

Start the backend in one PowerShell window:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another:

```powershell
Set-Location frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). FastAPI health endpoints are `http://localhost:8000/api/health` and `http://localhost:8000/api/health/database`.

## Tests and checks

From the repository root:

```powershell
python -m unittest discover -s backend/tests -v
Set-Location frontend
npm.cmd run build
Set-Location ..
```

The Neon integration test writes temporary test users and workout rows, then removes them. Run it only against a development database:

```powershell
$env:AI_GYM_NEON_TESTS = "1"
python -m unittest backend.tests.test_neon_integration -v
Remove-Item Env:AI_GYM_NEON_TESTS
```

Detector tests use synthetic landmark sequences. They check state transitions and visibility handling; they do not establish real-world accuracy for all people, camera angles, or movement speeds.

## Troubleshooting

- **OAuth `redirect_uri_mismatch`:** make the Google Console authorized redirect URI exactly equal to `GOOGLE_REDIRECT_URI`, including `/api/auth/google/callback`.
- **`SESSION_SECRET is not configured`:** set a random secret of at least 32 characters in `backend/.env`, then restart FastAPI.
- **Database connection fails:** confirm `DATABASE_URL` is pooled, `DIRECT_DATABASE_URL` is direct, both use the Psycopg 3 URL scheme, and the Neon project is available.
- **Frontend cannot reach the API:** check `frontend/.env`, restart Vite, and confirm `FRONTEND_ORIGIN` matches the browser origin.
- **Camera permission or preview fails:** allow camera access in the browser and use `localhost` or HTTPS. Close other apps holding the camera and retry.
- **WebRTC does not connect:** check network/firewall restrictions and configure TURN credentials if STUN alone is insufficient.
- **Pose model unavailable:** confirm `backend/ml_models/pose_landmarker_full.task` exists and the backend environment has compatible MediaPipe dependencies.
- **No form score appears:** a workout needs at least 30 valid detector frames; hidden joints and unsupported feedback states do not count.

## Current limitations and deployment notes

- The camera setup screen verifies camera access and shows a preview, but does not verify pose or required-joint visibility before the user continues. Pose status becomes available after workout processing starts.
- Active workout sessions and counters are in memory. A backend restart interrupts active workouts; completed history remains in Neon.
- Detector thresholds have synthetic tests but still need validation with real workout recordings and a range of camera positions.
- Browser/WebRTC/camera permission behavior and end-to-end Google sign-in need manual checks in the target deployment environment.
- Old history rows remain valid but have no form score. New completed sessions are stored separately with their own optional score.
- Production startup (`ENVIRONMENT=production`) validates HTTPS frontend and Google callback URLs, exact OAuth callback path, secure cookies, non-placeholder Google credentials, and a 32-character session secret. Set `FRONTEND_ORIGIN` to the deployed frontend's exact origin and authorize the exact `GOOGLE_REDIRECT_URI` in Google Cloud Console.
- Keep the frontend and API under the same site when using the default `AUTH_COOKIE_SAMESITE=lax`. If deployment uses unrelated sites, configure `AUTH_COOKIE_SAMESITE=none` and `COOKIE_SECURE=true`; browser cookie and OAuth behavior still needs verification on the deployed domains.
- Apply database changes with `python -m alembic upgrade head` from `backend/` before routing production traffic. Use a managed HTTPS host, exact CORS origin, production secrets, and an appropriate TURN service for restrictive networks.
