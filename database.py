import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get(
    "DIABUDDY_DATABASE",
    str(Path(__file__).resolve().parent / "instance" / "diabuddy.db"),
)


@contextmanager
def get_db(db_path=None):
    target_path = db_path or os.environ.get("DIABUDDY_DATABASE", DEFAULT_DB_PATH)
    parent_dir = Path(target_path).parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(target_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(db_path=None):
    with get_db(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value REAL NOT NULL CHECK (value > 0),
                unit TEXT NOT NULL CHECK (unit IN ('mg/dL', 'mmol/L')),
                context TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                recorded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                kind TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL CHECK (category IN ('Meal', 'Exercise', 'Sleep', 'Note')),
                summary TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                logged_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_readings_recorded_at ON readings(recorded_at);
            CREATE INDEX IF NOT EXISTS idx_reminders_scheduled_at ON reminders(scheduled_at);
            CREATE INDEX IF NOT EXISTS idx_journal_logged_at ON journal_entries(logged_at);
            """
        )

