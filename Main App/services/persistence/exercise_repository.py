import sqlite3#Connects Python to SQLite
import streamlit as st#Provides caching functionality
from pathlib import Path#Handles filesystem paths

_DB_PATH=str(Path(__file__).parent.parent/"data.db")
#__file__ represents the path of the current Python file.
@st.cache_resource
def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    # By default, SQLite restricts a connection to the thread that created it.
    # This argument disables that particular thread check.
    conn.row_factory = sqlite3.Row
    #Changes returned rows into objects that support column-name access.
    return conn


def init_db() -> None:
    conn = _get_connection()#Gets the cached database connection.

    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id),
                exercise_name TEXT    NOT NULL,
                reps          INTEGER NOT NULL DEFAULT 0,
                sets          INTEGER NOT NULL DEFAULT 0,
                time          INTEGER NOT NULL DEFAULT 0,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
#Retrieve a user
def get_user(username: str) -> sqlite3.Row:
    conn = _get_connection()

    return conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()#Retrieves the first matching row.

#Insert a new user
def create_user(username: str) -> sqlite3.Row:
    conn = _get_connection()
    
    with conn:
        conn.execute(
            "INSERT INTO users (username) VALUES (?)", (username,)
        )

    return get_user(username) 

def get_or_create_user(username: str) -> sqlite3.Row:
    init_db()
    user = get_user(username)

    if user is None:
        user = create_user(username)
    
    return user

def add_exercise(user_id, exercise_name, reps, sets, time):
    conn = _get_connection()

    with conn:
        #Search for an existing exercise
        existing = conn.execute("""
            SELECT * FROM exercises 
            WHERE user_id = ? AND exercise_name = ? AND Date('created_at') = Date('now')
        """, (user_id, exercise_name)).fetchone()

        if existing:
            #Adds the newly completed repetitions to the existing repetitions.
            conn.execute("""
                UPDATE exercises 
                SET reps = reps + ?, sets = sets + ?, time = time + ?
                WHERE id = ?
            """, (reps, sets, time, existing['id']))
        else:
            #INSERT a new exercise
            conn.execute("""
                INSERT INTO exercises (user_id, exercise_name, sets, reps, time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, exercise_name, sets, reps, time))
    get_users_exercises.clear()

@st.cache_data(ttl=30)
def get_users_exercises(user_id):
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM exercises 
        WHERE user_id = ?
    """, (user_id,)).fetchall()
    return [dict(row) for row in rows]