"""Daily Health Journal Service for DiaBuddy AI.

Enables tracking of meals, exercise, sleep, and lifestyle notes
to help identify patterns alongside glucose readings.
"""

from datetime import datetime
from database import get_db

JOURNAL_CATEGORIES = {"Meal", "Exercise", "Sleep", "Note"}


def parse_journal_form(form: dict) -> tuple[str, str, str, str]:
    """Validate and normalize journal entry form input."""
    category = form.get("category", "")
    summary = (form.get("summary") or "").strip()
    detail = (form.get("detail") or "").strip()
    logged_at_raw = form.get("logged_at", "")

    if category not in JOURNAL_CATEGORIES:
        raise ValueError("Choose a valid category: Meal, Exercise, Sleep, or Note.")
    if not summary or len(summary) > 200:
        raise ValueError("Summary is required and must be 200 characters or fewer.")
    if len(detail) > 500:
        raise ValueError("Detail notes must be 500 characters or fewer.")

    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(logged_at_raw.strip(), fmt)
            return category, summary, detail, parsed.isoformat(timespec="minutes")
        except (TypeError, ValueError):
            continue
    raise ValueError("Enter a valid journal date and time.")


def get_journal_entries(db_path=None, limit: int = 25) -> list[dict]:
    """Retrieve recent journal entries in reverse chronological order."""
    with get_db(db_path) as db:
        rows = db.execute(
            """
            SELECT * FROM journal_entries
            ORDER BY logged_at DESC, id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_journal_entry(
    category: str, summary: str, detail: str, logged_at: str, db_path=None
) -> int:
    with get_db(db_path) as db:
        cursor = db.execute(
            """
            INSERT INTO journal_entries (category, summary, detail, logged_at)
            VALUES (?, ?, ?, ?)
            """,
            (category, summary, detail, logged_at),
        )
        return cursor.lastrowid


def delete_journal_entry(entry_id: int, db_path=None) -> bool:
    with get_db(db_path) as db:
        result = db.execute(
            "DELETE FROM journal_entries WHERE id = ?", (entry_id,)
        )
        return result.rowcount > 0

