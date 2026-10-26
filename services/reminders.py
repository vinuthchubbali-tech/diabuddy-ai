"""Reminder management service for DiaBuddy AI."""

from datetime import datetime
import math
from database import get_db

REMINDER_TYPES = {"Medication", "Glucose check", "Other"}


def parse_reminder_form(form: dict) -> tuple[str, str, str]:
    """Validate and normalize reminder form input."""
    title = (form.get("title") or "").strip()
    kind = form.get("kind", "")
    scheduled_at_raw = form.get("scheduled_at", "")

    if not title or len(title) > 100:
        raise ValueError("Reminder title is required and must be 100 characters or fewer.")
    if kind not in REMINDER_TYPES:
        raise ValueError("Choose a valid reminder type (Medication, Glucose check, or Other).")

    try:
        parsed = datetime.strptime(scheduled_at_raw, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        raise ValueError("Enter a valid reminder date and time.") from None

    return title, kind, parsed.isoformat(timespec="minutes")


def get_reminders(db_path=None, limit: int = 10) -> tuple[list[dict], list[dict]]:
    """Retrieve upcoming pending reminders and recent completed reminders."""
    now_iso = datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")
    with get_db(db_path) as db:
        upcoming_rows = db.execute(
            """
            SELECT * FROM reminders
            WHERE completed = 0 AND scheduled_at >= ?
            ORDER BY scheduled_at ASC LIMIT ?
            """,
            (now_iso, limit),
        ).fetchall()

        recent_rows = db.execute(
            """
            SELECT * FROM reminders
            ORDER BY scheduled_at DESC, id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(r) for r in upcoming_rows], [dict(r) for r in recent_rows]


def add_reminder(title: str, kind: str, scheduled_at: str, db_path=None) -> int:
    with get_db(db_path) as db:
        cursor = db.execute(
            """
            INSERT INTO reminders (title, kind, scheduled_at)
            VALUES (?, ?, ?)
            """,
            (title, kind, scheduled_at),
        )
        return cursor.lastrowid


def complete_reminder(reminder_id: int, db_path=None) -> bool:
    with get_db(db_path) as db:
        result = db.execute(
            "UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,)
        )
        return result.rowcount > 0


def delete_reminder(reminder_id: int, db_path=None) -> bool:
    with get_db(db_path) as db:
        result = db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        return result.rowcount > 0
