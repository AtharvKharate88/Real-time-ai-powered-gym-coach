"""Repeat-safe migration of the legacy SQLite workout data into Neon."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database.session import SessionLocal
from models import Exercise, User


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace(" ", "T"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def migrate(source: Path) -> dict[str, int]:
    readonly_source = f"file:{source.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(readonly_source, uri=True) as sqlite_db:
        sqlite_db.row_factory = sqlite3.Row
        users = sqlite_db.execute(
            "SELECT id, username, created_at FROM users ORDER BY id"
        ).fetchall()
        exercises = sqlite_db.execute(
            """
            SELECT id, user_id, exercise_name, reps, sets, time, created_at
            FROM exercises
            ORDER BY id
            """
        ).fetchall()

    summary = {
        "users_inserted": 0,
        "users_skipped": 0,
        "user_conflicts": 0,
        "exercises_inserted": 0,
        "exercises_skipped": 0,
        "exercise_conflicts": 0,
    }

    with SessionLocal() as db:
        user_map: dict[int, int | None] = {}
        for row in users:
            created_at = parse_timestamp(row["created_at"])
            existing = db.get(User, row["id"])
            if existing is None:
                existing_by_name = db.scalar(
                    select(User).where(User.username == row["username"])
                )
                if existing_by_name is not None:
                    user_map[row["id"]] = existing_by_name.id
                    summary["users_skipped"] += 1
                    summary["user_conflicts"] += 1
                    continue
                db.add(
                    User(
                        id=row["id"],
                        username=row["username"],
                        **({"created_at": created_at} if created_at else {}),
                    )
                )
                user_map[row["id"]] = row["id"]
                summary["users_inserted"] += 1
            elif (
                existing.username == row["username"]
                and (created_at is None or existing.created_at == created_at)
            ):
                user_map[row["id"]] = existing.id
                summary["users_skipped"] += 1
            else:
                user_map[row["id"]] = None
                summary["users_skipped"] += 1
                summary["user_conflicts"] += 1

        db.flush()

        for row in exercises:
            target_user_id = (
                None
                if row["user_id"] in (None, 0)
                else user_map.get(row["user_id"])
            )
            created_at = parse_timestamp(row["created_at"])
            existing = db.get(Exercise, row["id"])
            if existing is not None:
                same = (
                    existing.user_id == target_user_id
                    and existing.exercise_name == row["exercise_name"]
                    and existing.reps == row["reps"]
                    and existing.sets == row["sets"]
                    and float(existing.time) == float(row["time"])
                    and (created_at is None or existing.created_at == created_at)
                )
                summary["exercises_skipped"] += 1
                summary["exercise_conflicts"] += int(not same)
                continue

            duplicate = db.scalar(
                select(Exercise).where(
                    Exercise.user_id == target_user_id,
                    Exercise.exercise_name == row["exercise_name"],
                    Exercise.reps == row["reps"],
                    Exercise.sets == row["sets"],
                    Exercise.time == float(row["time"]),
                    Exercise.created_at == created_at,
                )
            )
            if duplicate is not None:
                summary["exercises_skipped"] += 1
                continue

            exercise_values = dict(
                id=row["id"],
                user_id=target_user_id,
                exercise_name=row["exercise_name"],
                reps=row["reps"],
                sets=row["sets"],
                time=float(row["time"]),
            )
            if created_at is not None:
                exercise_values["created_at"] = created_at
            db.add(Exercise(**exercise_values))
            summary["exercises_inserted"] += 1

        db.commit()
        for table_name in ("users", "exercises"):
            maximum_id = db.scalar(text(f"SELECT MAX(id) FROM {table_name}"))
            if maximum_id is not None:
                db.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                        ":maximum_id, true)"
                    ),
                    {"table_name": table_name, "maximum_id": maximum_id},
                )
        db.commit()

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).parents[1] / "services" / "data.db",
    )
    args = parser.parse_args()
    if not args.source.is_file():
        raise FileNotFoundError(f"SQLite source does not exist: {args.source}")
    print(migrate(args.source))


if __name__ == "__main__":
    main()
