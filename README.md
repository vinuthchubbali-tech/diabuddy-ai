# 🩺 DiaBuddy AI

> **“Track Better. Understand More. Live Smarter.”**  
> *A local-first, privacy-conscious diabetes management companion and health-record explainer.*

---

## 💡 About DiaBuddy AI

Managing diabetes requires juggling multiple routines: tracking glucose numbers, remembering medications, noting meals, and attempting to spot health patterns across scattered records.

**DiaBuddy AI** brings all of these into one calm, private dashboard. It combines:
- 🩸 **Blood Glucose Tracking:** Record values (`mg/dL` or `mmol/L`), contexts (Fasting, Before meal, After meal, Other), timestamps, and notes.
- 📈 **Smart Analytics & Educational Benchmarks:** Calculates averages, highest/lowest readings, trends, and target adherence using general ADA educational reference ranges (Fasting: 80–130 mg/dL, Post-meal: <180 mg/dL).
- ✎ **Daily Health Journal:** Log meals, exercise, sleep, and lifestyle notes to help identify patterns alongside glucose readings.
- ⏰ **Routines & Reminders:** Set and manage daily medication or glucose-check alerts.
- 🤖 **Local AI Assistant (Ollama):** Ask questions about your logs in plain language using local models (e.g. `llama3.2`). Your health data never leaves your computer.

---

## 🛡️ Guiding Principle & Medical Disclaimer

> **“Record accurately. Explain clearly. Protect privacy. Never replace medical professionals.”**

DiaBuddy AI is a **personal health-record companion**, not an AI doctor.
- It **does not** provide medical diagnoses or prescriptions.
- It **never** calculates or recommends changes to insulin or medication dosages.
- Severe readings (< 70 mg/dL or > 250 mg/dL) or symptoms of distress trigger clear guidance to seek professional medical attention immediately.
- Always consult your endocrinologist or certified diabetes educator for individualized medical targets and care plans.

---

## 🗂️ Project Structure

```
diabuddy-ai/
│
├── app.py                   # Flask application routes and controllers
├── database.py              # SQLite schema, migrations, and connection manager
├── seed.py                  # Demo data generator (14-day sample dataset)
├── requirements.txt         # Core dependencies
├── README.md
│
├── services/                # Business logic services
│   ├── analytics.py         # Glucose stats, target classifications, and trend data
│   ├── reminders.py         # Medication & glucose check reminders
│   ├── journal.py           # Daily health journal (meals, exercise, sleep)
│   └── ai_assistant.py      # Ollama local LLM integration with safety guardrails
│
├── static/
│   ├── style.css            # Calm, responsive health-palette design system
│   └── script.js            # SVG chart renderer with target bands, quick chips
│
├── templates/
│   └── index.html           # Unified personal companion dashboard
│
├── tests/
│   ├── test_app.py          # End-to-end endpoint & CRUD test suite
│   └── test_analytics.py    # Analytics & educational classification tests
│
└── instance/
    └── diabuddy.db          # Local SQLite database (private, git-ignored)
```

---

## 🚀 Quickstart Guide

### 1. Requirements
- Python 3.10+
- (Optional) [Ollama](https://ollama.com/) if you want local AI summaries.

### 2. Setup Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. (Optional) Seed Realistic Demo Data for Hackathons
To explore the dashboard immediately with 14 days of sample readings, journal logs, and reminders:
```powershell
python seed.py
```
*(To wipe and reseed anytime: `python seed.py --clear`)*

### 4. Run DiaBuddy AI
```powershell
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

---

## 🤖 Running the Local AI Assistant with Ollama

DiaBuddy AI connects to Ollama running locally at `http://127.0.0.1:11434`.

1. Install [Ollama](https://ollama.com/) and pull a lightweight model:
   ```bash
   ollama pull llama3.2
   ```
2. Start the DiaBuddy app:
   ```powershell
   $env:OLLAMA_MODEL = "llama3.2"
   python app.py
   ```
3. Click any of the quick-prompt chips or type a question in the **Ask DiaBuddy AI** section.

---

## 🧪 Running Tests

Run the full automated test suite:
```powershell
python -m unittest discover -s tests
```

---

## 📄 License & Attribution

DiaBuddy AI is open-source software built for community health education and personal record keeping. Open-source contributions are warmly welcomed!
