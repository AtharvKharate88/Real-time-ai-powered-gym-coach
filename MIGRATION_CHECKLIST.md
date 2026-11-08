# React + FastAPI migration checklist

This checklist records the Phase 1 audit of the existing Streamlit application and
the current React/FastAPI foundation. Existing Streamlit functionality remains
available as a reference and fallback.

## Audited architecture

| Area | Existing implementation | React + FastAPI status |
| --- | --- | --- |
| Landing page | `frontend/src/components/LandingPage.tsx` | Present |
| Streamlit workout UI | `backend/main.py` | Preserved as fallback |
| FastAPI entry point | `backend/api/main.py` | Workout and WebRTC routes |
| Webcam transport | `streamlit_webrtc` in `backend/main.py` | React WebRTC + aiortc adapter |
| MediaPipe inference | `backend/services/vision/excercise_video_processor.py` | Reused by API sessions |
| Exercise detectors | `backend/detectors/*.py` | Reused unchanged by API sessions |
| Rep/set state | Streamlit session state and processor state | API-owned per-session processor state |
| SQLite persistence | `backend/services/persistence/exercise_repository.py` | API history persistence added |
| Groq coaching | `backend/services/coaching/llm.py` | API session integration |
| gTTS voice | `backend/services/coaching/tts.py` | API voice result endpoint |
| Async voice pipeline | `backend/services/coaching/voice_pipeline.py` | Reused asynchronously by API sessions |
| React API service | `frontend/src/services/api.ts` | Health endpoint integrated |
| Backend status UI | `frontend/src/components/BackendStatus.tsx` | Present |
| WebRTC API adapter | `backend/api/routes/webrtc.py` | Implemented; requires supported vision environment |

## Existing capabilities verified

- [x] Username login and SQLite user persistence
- [x] Squat detector
- [x] Push-up detector
- [x] Biceps curl detector
- [x] Shoulder press detector
- [x] Lunge detector
- [x] MediaPipe pose inference
- [x] Skeleton and exercise overlays
- [x] Rep counting and exercise-specific metrics
- [x] Set counting and workout completion
- [x] Streamlit workout controls and live metrics
- [x] Workout history aggregation
- [x] Groq coaching prompt and feedback logic
- [x] gTTS audio generation
- [x] Asynchronous voice queue, cooldowns, and stale-result replacement
- [x] STUN/TURN configuration for the existing Streamlit WebRTC path
- [x] Streamlit WebRTC frame dropping and video diagnostics

## Migration work remaining

### Backend integration

- [x] Define Pydantic request/response schemas.
- [x] Extract vision processing behind a FastAPI-compatible service boundary.
- [x] Preserve detector instances per workout session.
- [x] Add session lifecycle routes: initialize, start, pause, resume, stop.
- [x] Expose metrics, form status, and workout summary data.
- [x] Expose SQLite history without changing the database schema.
- [x] Adapt Groq and gTTS to the API service boundary.
- [x] Keep voice work asynchronous and non-blocking for frame processing.
- [x] Keep Streamlit-only imports out of health/session initialization paths.
- [x] Make the MediaPipe model path independent of the process working directory.

### Frontend integration

- [x] Add reusable workout page and control components.
- [x] Add exercise selection and workout configuration.
- [x] Add webcam permission and preview handling.
- [x] Add the selected real-time transport client.
- [x] Render processed video and workout metrics.
- [x] Render form status and AI coach feedback.
- [x] Add voice enable/disable and audio playback handling.
- [x] Add timer, rep/set progress, pause/resume/stop, and history views.
- [x] Add loading, permission, transport, and backend error states.

### Verification

- [ ] Test each detector through the migrated API independently with real exercise videos.
- [x] Test session state continuity across API metrics updates.
- [x] Test start, pause, resume, stop, and metrics lifecycle behavior.
- [x] Test missing coaching dependencies without stopping a workout.
- [ ] Test camera denial, disconnect, reconnection, and cleanup on a real browser.
- [x] Test React + FastAPI startup and WebRTC frame flow without Streamlit.
- [x] Compare migrated service boundaries with the Streamlit reference.

## Current implementation slice

- [x] FastAPI workout session schemas and in-memory session manager
- [x] Session start, pause, stop, and metrics endpoints
- [x] FastAPI WebRTC offer/answer adapter using `aiortc`
- [x] React workout controls, webcam preview, processed-video preview, and metrics polling
- [x] React WebRTC offer client
- [x] API-backed SQLite history and user migration
- [x] API-backed asynchronous Groq and gTTS feedback
- [x] React workout controls, timer, metrics, coaching, voice, and history

## Known migration risks

- The current vision processor subclasses `streamlit_webrtc.VideoProcessorBase`.
- The API now resolves the MediaPipe model relative to the backend package.
- Streamlit session state currently owns workout lifecycle and counters.
- SQLite uses one cached cross-thread connection and is not a server-grade
  multi-user storage layer.
- Groq and Google TTS require external services and may be unavailable.
- The default ICE configuration uses STUN only; restrictive networks may need
  TURN.
- No automated backend test suite was found during the audit.
