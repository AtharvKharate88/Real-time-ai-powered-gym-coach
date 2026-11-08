# Neon PostgreSQL migration

## Current architecture

- React calls the FastAPI API in `backend/api`.
- FastAPI and the original application persistence helpers share one SQLAlchemy engine, session factory, ORM models, and repositories under `backend/database` and `backend/models`.
- FastAPI traffic uses the Neon pooled `DATABASE_URL`; Alembic uses the direct `DIRECT_DATABASE_URL`.
- Google OAuth is the existing sign-in flow. The first successful Google callback creates a `users` row; no password-based authentication was added.
- Completed workouts are stored in PostgreSQL. Live webcam frames, pose results, timers, and counters remain in memory.
- Signed-in workouts are associated with the owner and history is filtered by that user. Anonymous workouts remain unassigned and visible through the existing unauthenticated history route.

## Configure the backend

Copy `backend/.env.example` to `backend/.env` and set:

```dotenv
DATABASE_URL=postgresql+psycopg://ROLE:PASSWORD@YOUR-POOLER-HOST/DATABASE?sslmode=require
DIRECT_DATABASE_URL=postgresql+psycopg://ROLE:PASSWORD@YOUR-DIRECT-HOST/DATABASE?sslmode=require
```

Keep the real URLs private. FastAPI validates that `DATABASE_URL` uses the Psycopg 3 driver and Neon pooler. Alembic validates that `DIRECT_DATABASE_URL` uses Psycopg 3 and is not pooled.

## Create or update the schema

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m alembic -c backend/alembic.ini upgrade head
```

The migrations create `users` and `exercises`, including Google identity fields and the user foreign key. Check connectivity through `GET /api/health/database`; it returns only a health status and does not expose database details.

## Transfer the legacy SQLite records

The one-time migration utility reads `backend/services/data.db` in read-only mode and inserts into Neon:

```powershell
python backend/scripts/migrate_sqlite_to_neon.py
```

Use `--source` to choose another SQLite file. The utility preserves IDs and timestamps, maps missing or invalid user references to anonymous records, reports conflicts, and safely skips records already present. Review the inserted/skipped/conflict counts and compare source and Neon counts after running it.

Do not remove `backend/services/data.db` or its backup until the migrated data has been checked and confirmed. The application itself does not open SQLite; only the one-time migration utility reads the retained source.

## Checks

```powershell
python -m unittest discover -s backend/tests -v
python -m compileall -q backend/api backend/database backend/models backend/migrations backend/scripts backend/tests
cd frontend
npm run build
```

Camera hardware, real Google OAuth, and a real browser/WebRTC session require manual environment checks; the automated tests cover API session ownership, persistence serialization, database health behavior, and logout cookie clearing.
