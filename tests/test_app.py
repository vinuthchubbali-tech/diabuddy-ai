import re
import tempfile
import unittest
from pathlib import Path

import app as diabuddy


class DiaBuddyAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        diabuddy.app.config.update(
            TESTING=True,
            DATABASE_PATH=self.db_path,
            SECRET_KEY="test-secret",
        )
        diabuddy.init_db(self.db_path)
        self.client = diabuddy.app.test_client()
        response = self.client.get("/")
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        self.csrf_token = match.group(1).decode()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_delete_reading(self):
        response = self.client.post(
            "/readings",
            data={
                "csrf_token": self.csrf_token,
                "value": "123.5",
                "unit": "mg/dL",
                "context": "Fasting",
                "notes": "Before breakfast",
                "recorded_at": "2026-10-26T08:30",
            },
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            reading_id = db.execute("SELECT id FROM readings").fetchone()["id"]

        page = self.client.get("/")
        self.assertIn(b"123.5", page.data)
        self.assertIn(b"Before breakfast", page.data)
        self.assertIn(b"In Range", page.data)

        response = self.client.post(
            f"/readings/{reading_id}/edit",
            data={
                "csrf_token": self.csrf_token,
                "value": "124",
                "unit": "mg/dL",
                "context": "After meal",
                "notes": "Updated note",
                "recorded_at": "2026-10-26T08:45",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(b"124", self.client.get("/").data)

        response = self.client.post(
            f"/readings/{reading_id}/delete",
            data={"csrf_token": self.csrf_token},
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 0)

    def test_chart_does_not_mix_measurement_units(self):
        with diabuddy.get_db(self.db_path) as db:
            db.executemany(
                """
                INSERT INTO readings (value, unit, context, notes, recorded_at)
                VALUES (?, ?, ?, '', ?)
                """,
                [
                    (120, "mg/dL", "Fasting", "2026-10-26T08:00"),
                    (6.7, "mmol/L", "Fasting", "2026-10-26T09:00"),
                ],
            )
        chart_readings = diabuddy.get_dashboard_data(self.db_path)["chart_readings"]
        self.assertEqual([row["unit"] for row in chart_readings], ["mmol/L"])

    def test_reading_date_filter(self):
        with diabuddy.get_db(self.db_path) as db:
            db.executemany(
                """
                INSERT INTO readings (value, unit, context, notes, recorded_at)
                VALUES (?, 'mg/dL', 'Fasting', '', ?)
                """,
                [(100, "2026-10-25T08:00"), (120, "2026-10-26T08:00")],
            )

        response = self.client.get("/?from_date=2026-10-26&to_date=2026-10-26")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"120", response.data)
        self.assertNotIn(b">100<", response.data)

    def test_rejects_invalid_reading_and_missing_csrf(self):
        response = self.client.post(
            "/readings",
            data={
                "csrf_token": self.csrf_token,
                "value": "-1",
                "unit": "mg/dL",
                "context": "Fasting",
                "recorded_at": "2026-10-26T08:30",
            },
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 0)

        response = self.client.post("/readings", data={"value": "100"})
        self.assertEqual(response.status_code, 400)

    def test_add_complete_and_delete_reminder(self):
        response = self.client.post(
            "/reminders",
            data={
                "csrf_token": self.csrf_token,
                "title": "Evening routine",
                "kind": "Medication",
                "scheduled_at": "2026-10-27T20:00",
            },
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            reminder_id = db.execute("SELECT id FROM reminders").fetchone()["id"]

        response = self.client.post(
            f"/reminders/{reminder_id}/complete",
            data={"csrf_token": self.csrf_token},
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            self.assertEqual(db.execute("SELECT completed FROM reminders").fetchone()[0], 1)

        response = self.client.post(
            f"/reminders/{reminder_id}/delete",
            data={"csrf_token": self.csrf_token},
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reminders").fetchone()[0], 0)

    def test_add_and_delete_journal_entry(self):
        response = self.client.post(
            "/journal",
            data={
                "csrf_token": self.csrf_token,
                "category": "Meal",
                "summary": "Oatmeal with almonds & blueberries",
                "detail": "~35g carbs",
                "logged_at": "2026-10-26T08:30",
            },
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            entry = db.execute("SELECT * FROM journal_entries").fetchone()
            self.assertIsNotNone(entry)
            self.assertEqual(entry["category"], "Meal")
            entry_id = entry["id"]

        page = self.client.get("/")
        self.assertIn(b"Oatmeal with almonds", page.data)

        # Delete entry
        response = self.client.post(
            f"/journal/{entry_id}/delete",
            data={"csrf_token": self.csrf_token},
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], 0)

    def test_reading_with_comma_and_seconds(self):
        response = self.client.post(
            "/readings",
            data={
                "csrf_token": self.csrf_token,
                "value": "115,8",
                "unit": "mg/dL",
                "context": "Fasting",
                "notes": "Comma support test",
                "recorded_at": "2026-10-26T08:30:45",
            },
        )
        self.assertEqual(response.status_code, 302)
        with diabuddy.get_db(self.db_path) as db:
            row = db.execute("SELECT value, recorded_at FROM readings").fetchone()
            self.assertAlmostEqual(row["value"], 115.8)
            self.assertEqual(row["recorded_at"], "2026-10-26T08:30")

    def test_assistant_api(self):
        # Without readings or journal, should return 400
        res = self.client.post(
            "/api/assistant",
            json={"question": "Summarize my readings"},
            headers={"X-CSRFToken": self.csrf_token},
        )
        self.assertEqual(res.status_code, 400)

        # Add a reading
        self.client.post(
            "/readings",
            data={
                "csrf_token": self.csrf_token,
                "value": "120",
                "unit": "mg/dL",
                "context": "Fasting",
                "recorded_at": "2026-10-26T08:30",
            },
        )

        # Now assistant returns 200 with structured response (via Ollama or intelligent fallback)
        res = self.client.post(
            "/api/assistant",
            json={"question": "Summarize my readings"},
            headers={"X-CSRFToken": self.csrf_token},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("answer", data)
        self.assertIn("DiaBuddy Summary", data["answer"])

    def test_doctor_report_route(self):
        # Add reading and journal entry
        self.client.post(
            "/readings",
            data={
                "csrf_token": self.csrf_token,
                "value": "118",
                "unit": "mg/dL",
                "context": "Fasting",
                "recorded_at": "2026-10-26T08:30",
            },
        )
        self.client.post(
            "/journal",
            data={
                "csrf_token": self.csrf_token,
                "category": "Meal",
                "summary": "Avocado toast",
                "logged_at": "2026-10-26T09:00",
            },
        )

        res = self.client.get("/report?days=14")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"DiaBuddy AI \xe2\x80\x94 Health Record Summary", res.data)
        self.assertIn(b"Avocado toast", res.data)
        self.assertIn(b"118", res.data)


if __name__ == "__main__":
    unittest.main()
