import unittest
from services.analytics import (
    classify_reading,
    compute_statistics,
    prepare_chart_data,
)


class AnalyticsServiceTests(unittest.TestCase):
    def test_classify_reading_targets(self):
        # Fasting: 80-130 mg/dL target
        self.assertEqual(classify_reading(110, "mg/dL", "Fasting")["status"], "in-range")
        self.assertEqual(classify_reading(145, "mg/dL", "Fasting")["status"], "above")
        self.assertEqual(classify_reading(75, "mg/dL", "Fasting")["status"], "below")

        # Hypoglycemia alert threshold: < 70 mg/dL
        low_res = classify_reading(65, "mg/dL", "Fasting")
        self.assertEqual(low_res["status"], "low")
        self.assertIn("Low Alert", low_res["label"])

        # Post-meal target: < 180 mg/dL
        self.assertEqual(classify_reading(160, "mg/dL", "After meal")["status"], "in-range")
        self.assertEqual(classify_reading(195, "mg/dL", "After meal")["status"], "above")

        # mmol/L support
        self.assertEqual(classify_reading(5.5, "mmol/L", "Fasting")["status"], "in-range")
        self.assertEqual(classify_reading(3.2, "mmol/L", "Fasting")["status"], "low")

    def test_compute_statistics(self):
        readings = [
            {"value": 100, "unit": "mg/dL", "context": "Fasting", "recorded_at": "2026-10-26T08:00"},
            {"value": 150, "unit": "mg/dL", "context": "After meal", "recorded_at": "2026-10-26T14:00"},
            {"value": 200, "unit": "mg/dL", "context": "After meal", "recorded_at": "2026-10-26T20:00"},
        ]
        stats = compute_statistics(readings)
        self.assertEqual(stats["total_count"], 3)
        self.assertAlmostEqual(stats["averages"]["mg/dL"], 150.0)
        self.assertEqual(stats["min_max"]["mg/dL"]["min"], 100)
        self.assertEqual(stats["min_max"]["mg/dL"]["max"], 200)
        # 100 is in range (fasting 80-130), 150 is in range (after meal < 180), 200 is above -> 2 of 3 in range = 66.7%
        self.assertEqual(stats["in_range_percent"], 66.7)

    def test_prepare_chart_data(self):
        readings = [
            {"value": 110, "unit": "mg/dL", "recorded_at": "2026-10-26T14:00"},
            {"value": 100, "unit": "mg/dL", "recorded_at": "2026-10-26T08:00"},
        ]
        chart_data = prepare_chart_data(readings)
        # Should be ordered chronologically
        self.assertEqual(chart_data[0]["value"], 100)
        self.assertEqual(chart_data[1]["value"], 110)


if __name__ == "__main__":
    unittest.main()
