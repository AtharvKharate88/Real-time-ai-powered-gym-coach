"""SQLite persistence for API workout sessions."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "services" / "data.db"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                reps INTEGER NOT NULL DEFAULT 0,
                sets INTEGER NOT NULL DEFAULT 0,
                time INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def add_exercise(
    exercise_name: str, reps: int, sets: int, elapsed_seconds: int
) -> None:
    initialize_database()
    with _connection() as connection:
        existing = connection.execute(
            """
            SELECT id FROM exercises
            WHERE user_id = 0 AND exercise_name = ?
              AND DATE(created_at) = DATE('now')
            """,
            (exercise_name,),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE exercises
                SET reps = reps + ?, sets = sets + ?, time = time + ?
                WHERE id = ?
                """,
                (reps, sets, elapsed_seconds, existing["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO exercises (user_id, exercise_name, reps, sets, time)
                VALUES (0, ?, ?, ?, ?)
                """,
                (exercise_name, reps, sets, elapsed_seconds),
            )


def get_history() -> list[dict[str, object]]:
    initialize_database()
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT exercise_name, reps, sets, time, created_at
            FROM exercises WHERE user_id = 0 ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]
