"""Seed script for DiaBuddy AI.

Generates realistic 14-day sample records for hackathons, testing,
and open-source demo purposes.
"""

import argparse
from datetime import datetime, timedelta
import random
from database import get_db, init_db


SAMPLE_READINGS = [
    # (days_ago, hour, minute, value, unit, context, notes)
    (13, 7, 30, 108.0, "mg/dL", "Fasting", "Morning baseline"),
    (13, 13, 45, 152.0, "mg/dL", "After meal", "Post-lunch (brown rice & tofu)"),
    (13, 20, 15, 134.0, "mg/dL", "After meal", "Dinner + 20 min evening walk"),
    (12, 7, 45, 114.0, "mg/dL", "Fasting", "Felt well rested"),
    (12, 12, 30, 98.0, "mg/dL", "Before meal", "Pre-lunch check"),
    (12, 14, 0, 168.0, "mg/dL", "After meal", "Higher carb lunch"),
    (11, 8, 0, 102.0, "mg/dL", "Fasting", "Good morning reading"),
    (11, 19, 30, 140.0, "mg/dL", "After meal", "Salad and grilled chicken"),
    (10, 7, 15, 122.0, "mg/dL", "Fasting", "Slept 6.5 hours"),
    (10, 14, 15, 178.0, "mg/dL", "After meal", "Work lunch meeting"),
    (9, 7, 50, 106.0, "mg/dL", "Fasting", "Consistent fasting trend"),
    (9, 13, 0, 110.0, "mg/dL", "Before meal", "Normal pre-lunch"),
    (9, 15, 0, 148.0, "mg/dL", "After meal", "Brisk 15 min walk after eating"),
    (8, 8, 10, 118.0, "mg/dL", "Fasting", "Weekend morning"),
    (8, 14, 30, 188.0, "mg/dL", "After meal", "Family brunch"),
    (7, 7, 40, 112.0, "mg/dL", "Fasting", "Start of the week"),
    (7, 13, 50, 142.0, "mg/dL", "After meal", "Lentil soup and avocado"),
    (6, 7, 35, 105.0, "mg/dL", "Fasting", "Normal fasting"),
    (6, 19, 45, 138.0, "mg/dL", "After meal", "Light dinner"),
    (5, 7, 25, 116.0, "mg/dL", "Fasting", "Coffee without sugar"),
    (5, 14, 10, 160.0, "mg/dL", "After meal", "Post-pasta lunch"),
    (4, 7, 50, 99.0, "mg/dL", "Fasting", "Under 100 fasting!"),
    (4, 13, 15, 105.0, "mg/dL", "Before meal", "Pre-lunch"),
    (4, 15, 20, 144.0, "mg/dL", "After meal", "Stepped outside for fresh air"),
    (3, 8, 0, 111.0, "mg/dL", "Fasting", "Consistent wake time"),
    (3, 14, 0, 155.0, "mg/dL", "After meal", "Standard lunch"),
    (2, 7, 30, 104.0, "mg/dL", "Fasting", "Morning hydration"),
    (2, 19, 30, 132.0, "mg/dL", "After meal", "Low-carb dinner"),
    (1, 8, 15, 109.0, "mg/dL", "Fasting", "Yesterday morning"),
    (1, 14, 15, 146.0, "mg/dL", "After meal", "Yesterday afternoon"),
    (0, 7, 45, 107.0, "mg/dL", "Fasting", "Today morning reading"),
]

SAMPLE_JOURNAL = [
    (10, "Meal", "Quinoa bowl with spinach, chickpeas, and olive oil", "Est. 40g complex carbs"),
    (9, "Exercise", "30-minute brisk walk in local park", "Moderate pace, ~3,500 steps"),
    (8, "Sleep", "7.5 hours uninterrupted sleep", "Woke up feeling refreshed"),
    (7, "Meal", "Greek yogurt with flaxseeds and handful of blueberries", "High protein breakfast"),
    (5, "Exercise", "25-minute bodyweight resistance routine", "Strength training at home"),
    (4, "Sleep", "8 hours restful sleep", "Slept before 11 PM"),
    (3, "Meal", "Grilled salmon with asparagus and side of sweet potato", "Balanced dinner"),
    (1, "Exercise", "40-minute outdoor cycling", "Good cardio session"),
    (0, "Note", "Feeling balanced and consistent with routines this week", "Hydrated with 2L water"),
]

SAMPLE_REMINDERS = [
    (1, "Morning Medication", "Medication", -1, 1),
    (1, "Post-Dinner Glucose Check", "Glucose check", -1, 1),
    (0, "Evening Routine Review", "Other", 4, 0),
    (0, "Nighttime Medication", "Medication", 8, 0),
    (-1, "Morning Glucose Check", "Glucose check", 24, 0),
]


def seed_database(clear_existing: bool = False, db_path: str = None):
    init_db(db_path)
    now = datetime.now()

    with get_db(db_path) as db:
        if clear_existing:
            db.execute("DELETE FROM readings")
            db.execute("DELETE FROM reminders")
            db.execute("DELETE FROM journal_entries")
            print("🧹 Cleared existing records.")

        # Seed readings
        for days_ago, hour, minute, val, unit, ctx, notes in SAMPLE_READINGS:
            dt = (now - timedelta(days=days_ago)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            db.execute(
                """
                INSERT INTO readings (value, unit, context, notes, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (val, unit, ctx, notes, dt.isoformat(timespec="minutes")),
            )

        # Seed journal entries
        for days_ago, category, summary, detail in SAMPLE_JOURNAL:
            dt = (now - timedelta(days=days_ago)).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            db.execute(
                """
                INSERT INTO journal_entries (category, summary, detail, logged_at)
                VALUES (?, ?, ?, ?)
                """,
                (category, summary, detail, dt.isoformat(timespec="minutes")),
            )

        # Seed reminders
        for day_offset, title, kind, hour_offset, completed in SAMPLE_REMINDERS:
            dt = (now + timedelta(days=day_offset, hours=hour_offset)).replace(
                minute=0, second=0, microsecond=0
            )
            db.execute(
                """
                INSERT INTO reminders (title, kind, scheduled_at, completed)
                VALUES (?, ?, ?, ?)
                """,
                (title, kind, dt.isoformat(timespec="minutes"), completed),
            )

    print(f"✨ Successfully seeded DiaBuddy AI database:")
    print(f"   • {len(SAMPLE_READINGS)} Glucose readings across 14 days")
    print(f"   • {len(SAMPLE_JOURNAL)} Health journal entries")
    print(f"   • {len(SAMPLE_REMINDERS)} Reminders (active & completed)")
    print(f"🚀 Ready for testing and hackathon demo!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed DiaBuddy AI database with demo records.")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    args = parser.parse_args()
    seed_database(clear_existing=args.clear)
