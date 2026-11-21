# Local workout validation

## Try the benchmark

From the repository root, run `npm.cmd --prefix frontend run dev`. Open the local address printed by Vite with `/?benchmark` appended. The benchmark does not require a login or a database connection. The normal workout also has a **Tracking performance** panel.

1. Choose an exercise. For example, record five squats using a device you control. Include the full movement from standing to squat and back to standing. Keep recordings local and get permission from anyone in frame.
2. Choose **Recording**, select that video and open **Mark the reps you can see in the recording**. Pause at each completed rep and press **Mark completed rep**. For a form error, mark both its beginning and end. Enter `[]` to label a clip as containing zero reps or zero errors. Leave labels blank when unknown.
3. Start the benchmark. It plays the recording at normal speed using the same detector as a live workout. Export the JSON after playback. Reuse the exact file and labels for each device or model comparison. Realtime replay may sample different frames as hardware speed changes.
4. For a sustained test, leave Recording empty, choose Front or Rear, and start the camera. Run for 20–30 minutes, then stop and export. Keep the tab visible. Backgrounding ends a benchmark run. The workout itself pauses and keeps its checkpoint.

Reports contain rep events, frame timings, visibility and error flags, browser and run settings. They exclude camera pixels and raw body landmarks. The comparison matches completed reps in order within half a second. It counts unmatched reference reps as missed and unmatched detector events as extra. Form precision, recall and F1 compare any detected form error with labeled intervals on each sampled frame. Those values depend on how much of the clip contains errors. Next-animation-frame latency measures time from starting inference to the next animation callback. Physical motion-to-display latency requires an external observation.

## Device trials still needed

Use a secure origin on each real phone for camera access. A laptop's LAN HTTP URL can load the page without granting camera access. Use a trusted local HTTPS development origin or device-supported secure localhost forwarding. A deployment is unnecessary for these trials.

| Trial | Record |
|---|---|
| Windows/macOS Chrome, Edge and Safari where supported | Browser and OS, front camera framing, denied permission and retry, visible overlay alignment, inferred FPS and p50/p95 latency |
| Android Chrome, Samsung Internet, iPhone/iPad Safari | Front and rear framing, switching at setup, rotation, portrait/landscape, home/lock and resume, camera interruption |
| Sustained workout | Compare the first and last five one-minute windows. Record elapsed time, device and browser version, battery change, charging state, warmth and OS-reported thermal warnings. Browser timing alone cannot establish temperature. |
| Accuracy | Include correct, incomplete, fast and slow reps, visibility loss, different bodies, front and side views, poor lighting, camera motion and a second person. Compare each exercise separately. |
| Model/delegate | Compare Full/CPU to Lite/CPU and supported GPU runs with identical clips. Full/CPU remains the workout default. GPU initialization failures are reported in the benchmark. |

## Persistence and repeatable tests

The browser saves an account- and workout-specific recovery record on this device, sends progress at set boundaries, pause and every 30 seconds of active time, and submits one final summary. Reopening the same exercise offers recoverable workouts, including synced ones on another signed-in device. During a network outage, recovery depends on available browser storage. Clearing storage before synchronization can lose pending changes.

The API authenticates the session cookie, checks account ownership, validates inputs and derives set breakdowns and form scores. A conditional PostgreSQL upsert rejects older revisions, decreasing totals, changed goals and changes after completion. A repeated identical final request returns success. Incomplete workouts and empty finishes stay out of history. Client-side counts describe what the browser reported and can be fabricated by a modified client.

From the repository root with frontend dependencies installed:

```powershell
npm.cmd --prefix frontend run build
backend/.venv/Scripts/python.exe frontend/scripts/check-squat-parity.py
backend/.venv/Scripts/python.exe frontend/scripts/check-exercise-parity.py
backend/.venv/Scripts/python.exe frontend/scripts/check-browser-workouts.py
backend/.venv/Scripts/python.exe backend/scripts/benchmark_local_workouts.py
```

The browser test uses an isolated Chrome profile, a simulated camera, generated video and a mock API. Set `CHROME_BIN` for a different Chromium executable. The API benchmark runs actual localhost HTTP, signed session cookies, database lookups and PostgreSQL transactions. It creates a temporary password-protected loopback cluster, applies the migration chain there, restarts the API process during each cohort and removes the temporary cluster. It needs local PostgreSQL binaries (set `PG_BIN` if necessary). The 10- and 30-user scenarios compress 30 minutes of logical workout time into bursts, with 60 checkpoint writes per user, concurrent duplicate finishes, history verification and cross-account denial. No Google OAuth provider, cloud database, GPU, Groq call or cloud deployment participates in these tests.

## Local API results, 21 November 2026

| Final measured run | 10 workout users | 30 workout users |
|---|---:|---:|
| Checkpoint writes | 600 | 1,800 |
| Checkpoint response p50 / p95 | 137 / 720 ms | 235 / 293 ms |
| Final save and duplicate retry p95 | 591 ms | 1,061 ms |
| History read p95 | 275 ms | 623 ms |
| Database pool acquisition p95, including connection setup and ping | 132 ms | 5 ms |
| Peak checked-out connections | 10 | 10 |
| Peak API process working set | 105 MiB | 118 MiB |
| API CPU seconds across both process lifetimes, after app import | 9.94 | 18.97 |
| Missing / duplicate history records | 0 / 0 | 0 / 0 |

The cohorts ran sequentially on a shared development machine. Cold connections and host load varied. The timing differences between cohorts do not establish a scaling curve. Cross-account access returned 403 and stale writes after completion returned 409 as expected. Neither running camera inference nor calling a hosted AI model was part of this API load test.

**Planning estimate.** Allow roughly 70 API calls per 30-minute workout for 60 periodic checkpoints, session verification, set boundaries, finalization and history. At 1,200 or 3,600 workouts per month, that yields about 84,000 or 252,000 API requests before extra retries or static assets. Both fit the published 2 million monthly Container Apps request grant if it is fully available. The earlier one/two active replica assumptions still imply about $0/$1.08 per month in eligible compute at the illustrative US rates, plus any ancillary meters. The benchmark measured local CPU work and memory. Azure bills allocated replica time, so a cloud bill cannot be derived from those CPU seconds alone. Grant availability, network egress, cold starts, background traffic and region can change the result. [Azure Container Apps pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)

