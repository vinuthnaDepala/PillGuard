# PillGuard — Product Requirements Document

# For: Claude Code implementation

# Hardware: Raspberry Pi 3B+, USB Webcam, HC-SR04 sensor, LED x2, 16x2 LCD, Speaker/Buzzer

---

## Project Overview

PillGuard is a smart pill dispenser system. A Raspberry Pi 3B+ monitors a pill box using an ultrasonic distance sensor. When the box is opened, a webcam records a 45-second clip. Frames are sampled and sent to Claude Vision API to classify what the patient did. The result is logged to a backend, alerts are sent via Twilio SMS, and a caretaker web dashboard displays the patient's medication history.

The system has two physical locations:

- **Pi side:** runs sensor polling, camera, Claude API calls, GPIO control
- **Laptop side:** runs FastAPI backend + serves React frontend (same WiFi network as Pi)

---

## Repository Structure

```
pillguard/
├── pi/
│   ├── pi_main.py
│   ├── claude_vision.py
│   └── lcd_controller.py
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── alerts.py
│   └── scheduler.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── History.jsx
│   │   │   └── Settings.jsx
│   │   └── components/
│   │       ├── AdherenceChart.jsx
│   │       ├── CalendarHeatmap.jsx
│   │       └── AlertFeed.jsx
│   └── package.json
├── .env
└── README.md
```

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
CARETAKER_PHONE=+1xxxxxxxxxx
BACKEND_URL=http://192.168.x.x:8000
```

All secrets loaded via `python-dotenv` on Pi and backend. Never hardcoded.

---

## Hardware + GPIO

### Components

- Raspberry Pi 3B+
- USB Webcam
- HC-SR04 Ultrasonic Distance Sensor
- Green LED
- Red LED
- 16x2 LCD Screen (I2C)
- Speaker/Buzzer

### GPIO Pin Assignments

```
HC-SR04 TRIG  → GPIO 23
HC-SR04 ECHO  → GPIO 24
Green LED     → GPIO 17
Red LED       → GPIO 27
Buzzer        → GPIO 22
LCD SDA       → GPIO 2  (I2C)
LCD SCL       → GPIO 3  (I2C)
```

### Sensor Logic

- Poll HC-SR04 every 500ms
- Baseline distance (lid closed) = ~30cm
- Trigger threshold = distance drops below 15cm
- Average 3 consecutive readings before triggering to debounce noisy sensor
- Once triggered, start camera capture sequence
- Do not re-trigger for 60 seconds after a trigger (cooldown)

---

## Pi Side — pi/pi_main.py

### Responsibilities

1. Poll sensor in a loop
2. On trigger: check if current time is within a scheduled pill window (±30 min)
   - If yes: normal flow
   - If no: POST unscheduled event to backend, still run full capture
3. Start webcam, record 45 seconds
4. Every 5 seconds: capture a frame, save as temp JPEG, send to claude_vision.py
5. Collect 9 frame classifications
6. Run majority vote → final state
7. DISTRESS overrides majority — any single DISTRESS = final state is DISTRESS
8. Control GPIO based on result (LED, buzzer)
9. Update LCD via lcd_controller.py
10. POST final result to backend `/event` endpoint
11. No-show is handled by backend scheduler, not Pi

### Camera

- Use OpenCV (cv2) to access USB webcam
- Capture at 640x480
- Save frames as `/tmp/frame_{n}.jpg`
- Delete temp frames after POST to backend

### Dependencies (install on Pi)

```
pip install anthropic opencv-python RPi.GPIO RPLCD requests python-dotenv
```

---

## Pi Side — pi/claude_vision.py

### Function: classify_frame(image_path) → dict

Sends a single frame to Claude Vision API and returns classification.

```python
def classify_frame(image_path):
    # 1. read image, detect media type from magic bytes (not extension)
    # 2. base64 encode
    # 3. call anthropic client with claude-sonnet-4-20250514
    # 4. parse JSON response
    # returns: {"state": str, "confidence": float, "reason": str}
```

### Media Type Detection (from magic bytes)

```python
with open(image_path, "rb") as f:
    header = f.read(8)
if header[:8] == b"\x89PNG\r\n\x1a\n":
    media_type = "image/png"
elif header[:3] == b"\xff\xd8\xff":
    media_type = "image/jpeg"
else:
    media_type = "image/png"
```

### Claude System Prompt

```
You are a medical monitoring AI watching an elderly Alzheimer's patient take their medication.
Analyze the image and classify exactly ONE of these states:

TOOK_PILL  - Person is clearly drinking, swallowing, or has pill/medicine moving toward mouth
NO_TAKE    - Person is present but not taking medication
DISTRESS   - Person has fallen, collapsed, is on the floor, or appears in physical distress
NO_SHOW    - No person visible in frame

Respond ONLY with a JSON object, no other text:
{
  "state": "TOOK_PILL" | "NO_TAKE" | "DISTRESS" | "NO_SHOW",
  "confidence": 0.0-1.0,
  "reason": "one sentence explanation"
}
```

### Majority Vote Logic

```python
from collections import Counter

def final_classification(frame_results):
    if any(r["state"] == "DISTRESS" for r in frame_results):
        return "DISTRESS"
    states = [r["state"] for r in frame_results]
    return Counter(states).most_common(1)[0][0]
```

---

## Pi Side — pi/lcd_controller.py

Uses `RPLCD` library with I2C. Display messages per state:

```
Idle:      Line1="PillGuard"      Line2="Ready"
Pill time: Line1="Time to take"   Line2="your medicine!"
TOOK_PILL: Line1="Great job!"     Line2="Pill logged"
NO_TAKE:   Line1="Please take"    Line2="your medicine"
DISTRESS:  Line1="Help coming"    Line2="Stay calm"
NO_SHOW:   Line1="Reminder:"      Line2="Take pill now!"
```

---

## Backend — backend/main.py

### Stack

- FastAPI
- SQLite via sqlite3 (no ORM)
- Twilio REST API for SMS
- APScheduler for no-show detection
- Uvicorn server
- Runs on laptop

### Dependencies

```
pip install fastapi uvicorn twilio apscheduler python-dotenv
```

### Database Schema — backend/database.py

```sql
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    caretaker_name TEXT,
    caretaker_phone TEXT,
    pill_schedule TEXT,      -- JSON string: [{"time": "08:00"}, {"time": "20:00"}]
    weekly_pill_count INTEGER DEFAULT 14
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    state TEXT NOT NULL,         -- TOOK_PILL | NO_TAKE | DISTRESS | NO_SHOW
    confidence REAL,
    reason TEXT,
    unscheduled INTEGER DEFAULT 0,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
```

Seed one default patient on first run so the Pi and dashboard work immediately without setup.

### API Endpoints

```
POST /event
  body: {
    patient_id: int,
    state: str,
    confidence: float,
    reason: str,
    unscheduled: bool
  }
  → logs to DB, triggers SMS, returns 200

GET /events/{patient_id}
  query params: limit (default 50)
  → returns list of events ordered by timestamp desc

GET /patient/{patient_id}
  → returns patient row

PUT /patient/{patient_id}/schedule
  body: { pill_schedule: [...], weekly_pill_count: int }
  → updates schedule

GET /stats/{patient_id}
  → returns:
    {
      today_taken: int,
      today_missed: int,
      week_adherence_pct: float,
      month_adherence_pct: float,
      daily_adherence: [{"date": "2026-04-11", "pct": 0.85}, ...]  // last 30 days
    }
```

### Twilio SMS — backend/alerts.py

Send SMS on every event. Templates:

```
TOOK_PILL:    "✅ {name} took their {time} medication."
NO_TAKE:      "⚠️ {name} opened pill box but did not take medication."
DISTRESS:     "🆘 ALERT: Possible fall detected for {name}. Check immediately."
NO_SHOW:      "⏰ {name} missed their {time} medication — did not approach dispenser."
UNSCHEDULED:  "ℹ️ {name} interacted with pill box at unscheduled time ({time})."
REFILL:       "💊 {name}'s weekly pill supply is running low. Please refill."
```

### No-Show Scheduler — backend/scheduler.py

- APScheduler runs a job at each time in patient's `pill_schedule`
- Job waits 30 minutes past scheduled time
- Checks if any `TOOK_PILL` event exists within that 30-minute window
- If not → logs `NO_SHOW` event + sends SMS
- Scheduler reloads when patient schedule is updated via PUT endpoint

### Refill Tracking

- Count `TOOK_PILL` events since last Monday 00:00
- When count reaches `weekly_pill_count - 2` → send refill SMS
- Do not send more than once per week

---

## Frontend — React + Vite + Tailwind + Recharts

### Setup

```
npm create vite@latest frontend -- --template react
cd frontend
npm install recharts tailwindcss @tailwindcss/vite
```

### Pages

**Dashboard.jsx — route: /**

- Patient name header
- Today's pill schedule with status (taken / missed / upcoming)
- Last event card: state badge + timestamp + reason text
- Alert feed: last 10 events as list (color coded by state)
- Stat cards: today's adherence %, current streak in days

**History.jsx — route: /history**

- Calendar heatmap: 30 days, color = green (took), red (missed), grey (no data)
- Line chart: daily adherence % over 30 days using Recharts LineChart
  - Add a linear regression trendline as a second line
  - If trendline slope is negative and current week < 70% → show warning banner: "Adherence declining — consult physician"
- Event table: all events, columns = timestamp | state | confidence | reason

**Settings.jsx — route: /settings**

- Patient name field
- Caretaker phone field
- Pill schedule builder: add/remove times
- Weekly pill count field
- Save button → PUT /patient/1/schedule

### State Colors

```
TOOK_PILL → green
NO_TAKE   → yellow/orange
DISTRESS  → red
NO_SHOW   → grey
```

### Data Fetching

- Poll GET /events/1 every 10 seconds for live updates (simple setInterval, no websocket needed)
- Poll GET /stats/1 every 30 seconds

---

## Error Handling Requirements

### Pi Side

- If Claude API call fails for a frame: skip that frame, do not crash
- If fewer than 3 frames return valid results: classify as NO_TAKE (safe default)
- If backend POST fails: log event locally to a file `/tmp/pillguard_fallback.log`
- If sensor gives impossible readings (>400cm or <0): discard and retry

### Backend Side

- If Twilio fails: log error but still return 200 to Pi (do not block the event log)
- All endpoints return proper HTTP status codes with error messages

### Frontend

- Show loading state while fetching
- Show "No data yet" empty state if events list is empty
- Handle backend being unreachable gracefully (show last cached data)

---

## Implementation Notes for Claude Code

1. Start with `backend/database.py` — create tables and seed default patient first
2. Build and test each FastAPI endpoint individually before moving on
3. `pi_main.py` should be runnable in simulation mode on a laptop (mock the GPIO calls with print statements) so backend integration can be tested without hardware
4. All GPIO code must be wrapped in try/except ImportError so the Pi code can be partially tested on a non-Pi machine
5. Frontend should work with hardcoded mock data first, then swap to real API calls
6. Use `python-dotenv` and load `.env` at the top of every file that needs secrets
7. No secret should ever be hardcoded in source files

---

## Simulation Mode (for testing without Pi hardware)

Add a `--simulate` flag to `pi_main.py`:

- Skips GPIO setup
- Instead of reading sensor, waits for keyboard input (press ENTER to simulate box open)
- Uses a test image instead of webcam
- Everything else (Claude API, backend POST) runs normally

This lets the backend and frontend be fully tested on a laptop before touching the Pi.
