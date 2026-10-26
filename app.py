import math
import os
import secrets
from datetime import date, datetime
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database import DEFAULT_DB_PATH, get_db, init_db
from services.ai_assistant import build_assistant_prompt, query_ollama
from services.analytics import (
    classify_reading,
    compute_statistics,
    prepare_chart_data,
)
from services.journal import (
    add_journal_entry,
    delete_journal_entry,
    get_journal_entries,
    parse_journal_form,
)
from services.reminders import (
    add_reminder,
    complete_reminder,
    delete_reminder,
    get_reminders,
    parse_reminder_form,
)

app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["DATABASE_PATH"] = os.environ.get("DIABUDDY_DATABASE", DEFAULT_DB_PATH)
Path(app.instance_path).mkdir(parents=True, exist_ok=True)

READING_CONTEXTS = {"Fasting", "Before meal", "After meal", "Other"}


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        supplied = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
        expected = session.get("_csrf_token", "")
        if not expected or not secrets.compare_digest(supplied, expected):
            abort(400, description="The form expired. Refresh the page and try again.")


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": csrf_token}


def parse_datetime(value: str, field_name: str) -> str:
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value.strip(), fmt)
            return parsed.isoformat(timespec="minutes")
        except (TypeError, ValueError):
            continue
    raise ValueError(f"Enter a valid {field_name.lower()}.")


def parse_reading(form):
    raw_val = (form.get("value") or "").strip().replace(",", ".")
    try:
        value = float(raw_val)
    except (TypeError, ValueError):
        raise ValueError("Enter a numeric glucose value.") from None
    if not math.isfinite(value) or value <= 0 or value > 10000:
        raise ValueError("Glucose value must be greater than 0 and no more than 10,000.")

    unit = form.get("unit", "")
    context = form.get("context", "")
    notes = form.get("notes", "").strip()
    if unit not in {"mg/dL", "mmol/L"}:
        raise ValueError("Choose mg/dL or mmol/L.")
    if context not in READING_CONTEXTS:
        raise ValueError("Choose a valid reading context.")
    if len(notes) > 500:
        raise ValueError("Notes must be 500 characters or fewer.")
    recorded_at = parse_datetime(form.get("recorded_at", ""), "date and time")
    return value, unit, context, notes, recorded_at


def get_dashboard_data(db_path=None):
    target_db = db_path or app.config["DATABASE_PATH"]
    now = datetime.now().replace(second=0, microsecond=0)

    with get_db(target_db) as db:
        all_readings = db.execute(
            "SELECT * FROM readings ORDER BY recorded_at DESC, id DESC"
        ).fetchall()

    readings = [dict(row) for row in all_readings]
    # Augment readings with educational classification badges
    for r in readings:
        r["classification"] = classify_reading(r["value"], r["unit"], r["context"])

    stats = compute_statistics(readings)
    chart_readings = prepare_chart_data(readings, limit=30)
    upcoming_reminders, recent_reminders = get_reminders(target_db, limit=8)
    journal_entries = get_journal_entries(target_db, limit=12)

    return {
        "readings": readings,
        "chart_readings": chart_readings,
        "latest": readings[0] if readings else None,
        "stats": stats,
        "weekly_count": stats["weekly_count"],
        "weekly_delta": stats["weekly_delta"],
        "averages": stats["averages"],
        "min_max": stats["min_max"],
        "in_range_percent": stats["in_range_percent"],
        "upcoming_reminders": upcoming_reminders,
        "recent_reminders": recent_reminders,
        "journal_entries": journal_entries,
        "now_local": now.isoformat(timespec="minutes"),
    }


# Backwards compatibility alias
dashboard_data = get_dashboard_data


@app.get("/")
def index():
    data = get_dashboard_data()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()
    try:
        start = date.fromisoformat(from_date) if from_date else None
        end = date.fromisoformat(to_date) if to_date else None
        if start and start.isoformat() != from_date or end and end.isoformat() != to_date:
            raise ValueError
        if start and end and start > end:
            flash("The start date must be on or before the end date.", "error")
            start = end = None
    except ValueError:
        flash("Enter a valid date range.", "error")
        start = end = None

    data["visible_readings"] = [
        reading
        for reading in data["readings"]
        if (start is None or reading["recorded_at"][:10] >= start.isoformat())
        and (end is None or reading["recorded_at"][:10] <= end.isoformat())
    ]
    if start is not None or end is not None:
        data["chart_readings"] = prepare_chart_data(data["visible_readings"], limit=30)
    data["from_date"] = from_date
    data["to_date"] = to_date
    return render_template("index.html", **data)


@app.post("/readings")
def add_reading_route():
    try:
        reading = parse_reading(request.form)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("index") + "#readings")
    with get_db(app.config["DATABASE_PATH"]) as db:
        db.execute(
            """
            INSERT INTO readings (value, unit, context, notes, recorded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            reading,
        )
    flash("Glucose reading saved successfully.", "success")
    return redirect(url_for("index") + "#readings")


@app.post("/readings/<int:reading_id>/edit")
def edit_reading_route(reading_id):
    try:
        reading = parse_reading(request.form)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("index") + "#readings")
    with get_db(app.config["DATABASE_PATH"]) as db:
        result = db.execute(
            """
            UPDATE readings
            SET value = ?, unit = ?, context = ?, notes = ?, recorded_at = ?
            WHERE id = ?
            """,
            (*reading, reading_id),
        )
    if result.rowcount == 0:
        abort(404)
    flash("Glucose reading updated.", "success")
    return redirect(url_for("index") + "#readings")


@app.post("/readings/<int:reading_id>/delete")
def delete_reading_route(reading_id):
    with get_db(app.config["DATABASE_PATH"]) as db:
        result = db.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
    if result.rowcount == 0:
        abort(404)
    flash("Glucose reading deleted.", "success")
    return redirect(url_for("index") + "#readings")


@app.post("/reminders")
def add_reminder_route():
    try:
        title, kind, scheduled_at = parse_reminder_form(request.form)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("index") + "#reminders")
    add_reminder(title, kind, scheduled_at, db_path=app.config["DATABASE_PATH"])
    flash("Reminder scheduled.", "success")
    return redirect(url_for("index") + "#reminders")


@app.post("/reminders/<int:reminder_id>/complete")
def complete_reminder_route(reminder_id):
    if not complete_reminder(reminder_id, db_path=app.config["DATABASE_PATH"]):
        abort(404)
    flash("Reminder marked complete.", "success")
    return redirect(url_for("index") + "#reminders")


@app.post("/reminders/<int:reminder_id>/delete")
def delete_reminder_route(reminder_id):
    if not delete_reminder(reminder_id, db_path=app.config["DATABASE_PATH"]):
        abort(404)
    flash("Reminder removed.", "success")
    return redirect(url_for("index") + "#reminders")


@app.post("/journal")
def add_journal_route():
    try:
        category, summary, detail, logged_at = parse_journal_form(request.form)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("index") + "#journal")
    add_journal_entry(
        category, summary, detail, logged_at, db_path=app.config["DATABASE_PATH"]
    )
    flash(f"Journal entry for {category.lower()} saved.", "success")
    return redirect(url_for("index") + "#journal")


@app.post("/journal/<int:entry_id>/delete")
def delete_journal_route(entry_id):
    if not delete_journal_entry(entry_id, db_path=app.config["DATABASE_PATH"]):
        abort(404)
    flash("Journal entry deleted.", "success")
    return redirect(url_for("index") + "#journal")


@app.post("/api/assistant")
def assistant():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Send a JSON object with a question."), 400
    question = body.get("question", "")
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        return jsonify(error="Enter a question between 1 and 500 characters."), 400

    dash_data = get_dashboard_data()
    readings = dash_data["readings"]
    journal = dash_data["journal_entries"]

    if not readings and not journal:
        return (
            jsonify(
                error="Add at least one glucose reading or journal entry before asking for an AI summary."
            ),
            400,
        )

    prompt = build_assistant_prompt(question, readings, journal)
    answer, is_ai = query_ollama(prompt, question, readings, journal)
    return jsonify(answer=answer, is_ai=is_ai)


init_db(app.config["DATABASE_PATH"])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
