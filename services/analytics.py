"""Smart Glucose Analytics Engine for DiaBuddy AI.

Provides statistical summaries, trend calculations, and educational
reference benchmarks (ADA general guidelines).
"""

from datetime import datetime, timedelta

# Educational reference ranges based on ADA general guidelines:
# - Fasting / Before meal: 80-130 mg/dL (4.4-7.2 mmol/L)
# - Post-meal: < 180 mg/dL (< 10.0 mmol/L)
# - Severe Low alert threshold: < 70 mg/dL (< 3.9 mmol/L)
TARGET_RANGES = {
    "mg/dL": {
        "severe_low": 70,
        "Fasting": (80, 130),
        "Before meal": (80, 130),
        "After meal": (80, 180),
        "Other": (80, 140),
    },
    "mmol/L": {
        "severe_low": 3.9,
        "Fasting": (4.4, 7.2),
        "Before meal": (4.4, 7.2),
        "After meal": (4.4, 10.0),
        "Other": (4.4, 7.8),
    },
}


def classify_reading(value: float, unit: str, context: str) -> dict:
    """Classify a reading against educational reference targets.

    Returns a dict with 'status' (in-range, above, below, low) and 'label'.
    """
    ranges = TARGET_RANGES.get(unit, TARGET_RANGES["mg/dL"])
    severe_low = ranges["severe_low"]
    low_bound, high_bound = ranges.get(context, ranges["Other"])

    if value < severe_low:
        return {
            "status": "low",
            "badge_class": "badge-low",
            "label": "Low Alert (<" + str(severe_low) + ")",
        }
    if value < low_bound:
        return {
            "status": "below",
            "badge_class": "badge-below",
            "label": "Below Target",
        }
    if value > high_bound:
        return {
            "status": "above",
            "badge_class": "badge-above",
            "label": "Above Target",
        }
    return {
        "status": "in-range",
        "badge_class": "badge-in-range",
        "label": "In Range",
    }


def compute_statistics(readings: list[dict]) -> dict:
    """Calculate summary statistics, trends, and time-in-range for readings."""
    if not readings:
        return {
            "total_count": 0,
            "weekly_count": 0,
            "previous_weekly_count": 0,
            "weekly_delta": 0,
            "averages": {},
            "min_max": {},
            "in_range_percent": None,
            "context_breakdown": {},
        }

    now = datetime.now().replace(second=0, microsecond=0)
    seven_days_ago = (now - timedelta(days=7)).isoformat(timespec="minutes")
    fourteen_days_ago = (now - timedelta(days=14)).isoformat(timespec="minutes")

    weekly_readings = [r for r in readings if r["recorded_at"] >= seven_days_ago]
    previous_weekly_readings = [
        r
        for r in readings
        if fourteen_days_ago <= r["recorded_at"] < seven_days_ago
    ]

    # Calculate per-unit averages, min, max
    averages = {}
    min_max = {}
    for unit in ("mg/dL", "mmol/L"):
        unit_readings = [r for r in readings if r["unit"] == unit]
        if unit_readings:
            values = [r["value"] for r in unit_readings]
            averages[unit] = sum(values) / len(values)
            min_entry = min(unit_readings, key=lambda r: r["value"])
            max_entry = max(unit_readings, key=lambda r: r["value"])
            min_max[unit] = {
                "min": min_entry["value"],
                "min_date": min_entry["recorded_at"][:10],
                "max": max_entry["value"],
                "max_date": max_entry["recorded_at"][:10],
            }

    # Time-in-range calculation across all readings
    in_range_count = sum(
        1
        for r in readings
        if classify_reading(r["value"], r["unit"], r["context"])["status"]
        == "in-range"
    )
    in_range_percent = (
        round((in_range_count / len(readings)) * 100, 1) if readings else None
    )

    # Context distribution
    context_breakdown = {}
    for r in readings:
        ctx = r["context"]
        context_breakdown[ctx] = context_breakdown.get(ctx, 0) + 1

    return {
        "total_count": len(readings),
        "weekly_count": len(weekly_readings),
        "previous_weekly_count": len(previous_weekly_readings),
        "weekly_delta": len(weekly_readings) - len(previous_weekly_readings),
        "averages": averages,
        "min_max": min_max,
        "in_range_percent": in_range_percent,
        "context_breakdown": context_breakdown,
    }


def prepare_chart_data(readings: list[dict], limit: int = 30) -> list[dict]:
    """Prepare chronological data points for the trend chart.

    Only uses readings of the most recent reading's unit to avoid mixing scales.
    """
    if not readings:
        return []
    chart_unit = readings[0]["unit"]
    matched = [r for r in readings if r["unit"] == chart_unit][:limit]
    # Reverse so the chart flows chronologically (left to right)
    return list(reversed(matched))


def generate_health_insights(
    readings: list[dict], journal: list[dict] | None = None
) -> list[dict]:
    """Generate objective, non-diagnostic observational insights from recorded logs.

    Insights explain data volume, compare contexts, and avoid claiming direct causation.
    """
    insights = []
    if not readings:
        return [
            {
                "icon": "💡",
                "tag": "Getting Started",
                "title": "Begin your record habit",
                "body": "Recording 2 to 3 readings a day (e.g. morning fasting and post-meal) provides the baseline needed to uncover daily patterns.",
            }
        ]

    stats = compute_statistics(readings)
    now = datetime.now()

    # 1. Tracking Frequency & Consistency
    weekly_cnt = stats["weekly_count"]
    delta = stats["weekly_delta"]
    if delta > 0:
        insights.append(
            {
                "icon": "📈",
                "tag": "Consistency",
                "title": f"Logging frequency increased (+{delta} this week)",
                "body": f"You logged {weekly_cnt} readings in the last 7 days. Higher logging frequency helps build a reliable health record.",
            }
        )
    elif delta < 0 and abs(delta) >= 3:
        insights.append(
            {
                "icon": "ℹ️",
                "tag": "Observation",
                "title": f"Fewer entries logged this week ({weekly_cnt} vs {stats['previous_weekly_count']})",
                "body": "Logging consistently across both weekdays and weekends provides a more complete picture for your doctor.",
            }
        )
    else:
        insights.append(
            {
                "icon": "🎯",
                "tag": "Routine",
                "title": f"Steady recording routine ({weekly_cnt} this week)",
                "body": "Your recording volume is steady. Consistent data gives your healthcare team clear visibility into your routine.",
            }
        )

    # 2. Fasting vs Post-meal comparison
    fasting = [r["value"] for r in readings if r.get("context") == "Fasting"]
    after_meal = [r["value"] for r in readings if r.get("context") == "After meal"]
    unit = readings[0]["unit"]

    if fasting and after_meal:
        f_avg = sum(fasting) / len(fasting)
        p_avg = sum(after_meal) / len(after_meal)
        diff = p_avg - f_avg
        if diff > 0:
            insights.append(
                {
                    "icon": "🍽️",
                    "tag": "Context Pattern",
                    "title": f"Post-meal entries average {diff:.0f} {unit} higher than fasting",
                    "body": f"Fasting average: {f_avg:.1f} {unit} · Post-meal average: {p_avg:.1f} {unit}. Post-prandial rises are natural; review this spread with your clinician.",
                }
            )
        else:
            insights.append(
                {
                    "icon": "🍽️",
                    "tag": "Context Pattern",
                    "title": f"Post-meal and fasting averages are close",
                    "body": f"Fasting: {f_avg:.1f} {unit} · Post-meal: {p_avg:.1f} {unit}. Stable averages suggest balanced meal compositions.",
                }
            )

    # 3. Target Range Adherence
    in_range = stats["in_range_percent"]
    if in_range is not None:
        if in_range >= 70:
            insights.append(
                {
                    "icon": "⭐",
                    "tag": "Adherence",
                    "title": f"{in_range}% of readings within general target ranges",
                    "body": "A strong majority of your recorded readings fall within ADA reference guidelines (Fasting 80–130, Post-meal <180 mg/dL).",
                }
            )
        else:
            insights.append(
                {
                    "icon": "📊",
                    "tag": "Educational Target",
                    "title": f"{in_range}% of readings currently in reference target range",
                    "body": "Discuss these recorded ranges with your healthcare professional to customize targets specific to your care plan.",
                }
            )

    # 4. Lifestyle Journal Observations
    if journal:
        exercise_entries = [j for j in journal if j.get("category") == "Exercise"]
        sleep_entries = [j for j in journal if j.get("category") == "Sleep"]
        if exercise_entries:
            insights.append(
                {
                    "icon": "🏃",
                    "tag": "Lifestyle Observation",
                    "title": f"{len(exercise_entries)} physical activities tracked",
                    "body": "Active movement was logged alongside your readings. Comparing exercise days to glucose trends can reveal helpful routines.",
                }
            )
        elif sleep_entries:
            insights.append(
                {
                    "icon": "🌙",
                    "tag": "Rest & Routine",
                    "title": f"{len(sleep_entries)} sleep records logged",
                    "body": "Regular sleep schedules help maintain insulin sensitivity. Continue tracking your sleep duration alongside readings.",
                }
            )

    return insights[:4]


