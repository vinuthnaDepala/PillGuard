# PillGuard

link to project video: https://www.youtube.com/watch?v=BdO7LEJNPOE&feature=youtu.be

> A smart medication dispenser that watches over elderly patients — and calls for help when something goes wrong.

PillGuard pairs a Raspberry Pi with Claude Vision to answer one simple question every time a pill box is opened: **did the patient actually take their medication, or is something wrong?**

When the pill box lid opens, a USB webcam captures 15 frames over 15 seconds. Claude analyzes the whole sequence as a story — not just isolated frames — and decides whether the patient took the pill, skipped it, or fell. A caretaker gets an email alert within seconds, and a live web dashboard tracks adherence over time.

---

## Why this exists

Around **50% of elderly patients** with chronic conditions don't take their medications as prescribed. For patients with Alzheimer's or dementia, the numbers are worse — and the consequences are severe. Existing "smart pill boxes" just beep and assume the patient heard them. They can't tell the difference between a patient who took their pill, a patient who opened the box and wandered off, and a patient who collapsed on the floor.

PillGuard sees the difference.

---

## How it works

```
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │  HC-SR04     │     │  Raspberry   │     │   Claude     │
   │  ultrasonic  │────▶│  Pi 3B+      │────▶│   Vision     │
   │  sensor      │     │              │     │   API        │
   └──────────────┘     │  • webcam    │     └──────┬───────┘
                        │  • LEDs      │            │
                        │  • buzzer    │            ▼
                        │  • LCD       │     ┌──────────────┐
                        └──────┬───────┘     │  state +     │
                               │             │  confidence  │
                               ▼             │  + reason    │
                        ┌──────────────┐     └──────┬───────┘
                        │  FastAPI     │◀───────────┘
                        │  backend     │
                        │              │
                        │  • SQLite    │
                        │  • scheduler │
                        │  • SMTP      │
                        └──────┬───────┘
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
            ┌─────────────┐         ┌─────────────┐
            │   React     │         │  Caretaker  │
            │  dashboard  │         │    email    │
            └─────────────┘         └─────────────┘
```

1. **Sensor triggers.** The ultrasonic sensor detects the lid opening when distance drops below 15 cm for 3 consecutive readings (debounced).
2. **Camera captures.** USB webcam records 15 frames over 15 seconds — enough to see a full pill-taking gesture.
3. **Claude classifies.** All 15 frames are sent in a *single* API call so Claude can reason about the sequence as a whole. Motion across frames is a critical signal — a frozen, abnormal posture is a distress flag even if any single frame looks ambiguous.
4. **System responds.** Green LED + quick buzz for `TOOK_PILL`, red LED + long buzz for `NO_TAKE`, and a distress escalation for `DISTRESS`. LCD shows a calming message.
5. **Backend logs it.** FastAPI writes the event to SQLite, sends an SMTP email to the caretaker, and updates live stats.
6. **Dashboard shows it.** React frontend polls for events and renders schedule status, streaks, 30-day adherence trends, and a calendar heatmap.

---

## Features

### Vision
- **Single-batch Claude API call** — all 15 frames per trigger go in one request, so the model reasons about the whole scene (not 15 isolated frames voted up or down).
- **Motion-aware DISTRESS detection** — "head tilted back + no movement across 15 seconds" is treated as a medical emergency, not a sleeping patient.
- **Broad TOOK_PILL definition** — reaching toward the mouth, drinking water to wash a pill down, or holding a cup near the face all count.
- **Frame archive** — every capture is saved to `~/pillguard_frames/<timestamp>/` along with `results.json` so you can audit exactly what Claude saw for any decision.

### Active reminders
- **Scheduled pill times** from the dashboard. When the window opens, the Pi starts an *active reminder*: flashing LEDs + continuous buzzer until the patient physically opens the box.
- **Early-take grace window** — if the patient takes their pill 30 minutes early, the upcoming reminder is automatically suppressed.
- **Reminder cleared on box open** — the moment the sensor debounces a trigger, the alarm stops so the classification pipeline can take over.

### Caretaker alerts
- **Email via SMTP** (Gmail-compatible) on every event — took pill, missed pill, distress, unscheduled box interaction, and weekly refill warnings.
- **Twilio SMS** scaffolded in as a secondary channel (requires toll-free verification).
- **Doesn't block on failure** — if email fails, the event is still logged so the dashboard stays accurate.

### Dashboard
- **Live stat cards** — today taken, today missed, week adherence %, current streak.
- **Today's schedule** with per-slot status (upcoming / current / taken / missed).
- **Recent alerts** feed — color-coded by state.
- **30-day adherence chart** with linear-regression trendline. If the trend is declining and the week is under 70%, it flags "Adherence declining — consult physician."
- **Calendar heatmap** — 30-day grid, 4-tier color scale.
- **Full event table** with confidence and Claude's reasoning per event.
- **Settings page** to edit patient info, caretaker contact, and pill schedule — updates hot-reload the scheduler.

### Resilience
- **Offline fallback** — if the backend POST fails, events are appended to `/tmp/pillguard_fallback.log`.
- **Cached UI** — dashboard keeps showing last-known data when the backend is unreachable.
- **Sensor validation** — impossible readings (>400cm, <0) are discarded.
- **60-second cooldown** after every trigger prevents duplicate captures.

---

## Hardware

| Component | Pin / Interface |
|---|---|
| Raspberry Pi 3B+ | — |
| USB Webcam | USB |
| HC-SR04 ultrasonic sensor | TRIG → GPIO 23, ECHO → GPIO 24 *(with 1kΩ + 2kΩ voltage divider on ECHO)* |
| Green LED | GPIO 17 |
| Red LED | GPIO 27 |
| Passive buzzer | GPIO 22 *(PWM at 1–2 kHz)* |
| Grove RGB LCD 16×2 | I²C — text at `0x3e`, backlight at `0x62` |

---

## Repository layout

```
PillGuard/
├── pi/
│   ├── pi_main.py          # Main loop: sensor poll, capture, classify, respond
│   ├── claude_vision.py    # Batched Claude Vision classifier
│   ├── lcd_controller.py   # Grove RGB LCD driver (smbus2)
│   └── sensor_test.py      # Standalone sensor debounce/cooldown visualizer
├── backend/
│   ├── main.py             # FastAPI app
│   ├── database.py         # SQLite schema + queries
│   ├── alerts.py           # SMTP + Twilio
│   └── scheduler.py        # APScheduler no-show detection
├── frontend/
│   └── src/
│       ├── pages/          # Dashboard, History, Settings
│       └── components/     # AlertFeed, AdherenceChart, CalendarHeatmap
├── .env                    # secrets (not committed)
└── CLAUDE.md               # full product spec
```

---

## Setup

### 1. Clone + env

```bash
git clone <this-repo>
cd PillGuard
cp .env.example .env    # then fill in the values below
```

Required environment variables:

```bash
ANTHROPIC_API_KEY=sk-ant-...

# Email alerts (Gmail app password — requires 2-Step Verification enabled)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx    # 16-char Google app password
SMTP_FROM=your@gmail.com
CARETAKER_EMAIL=caretaker@example.com

# Optional: SMS alerts
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
CARETAKER_PHONE=+1...

# Pi → laptop (use the laptop's LAN IP, not localhost)
BACKEND_URL=http://192.168.x.x:8000
```

### 2. Backend (laptop)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn apscheduler python-dotenv anthropic twilio
python main.py
# → runs on http://0.0.0.0:8000
```

The first run auto-creates `pillguard.db` and seeds a default patient.

### 3. Frontend (laptop)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

The Vite config proxies `/api/*` to the FastAPI server.

### 4. Pi

```bash
# On the Pi
python3 -m venv --system-site-packages .venv   # --system-site-packages lets venv see apt-installed opencv
source .venv/bin/activate
pip install anthropic requests python-dotenv smbus2 RPi.GPIO
python -m pi.pi_main
```

### Simulation mode (no hardware)

Test the whole pipeline on a laptop without a Pi:

```bash
python -m pi.pi_main --simulate --test-image path/to/test.jpg
```

Press ENTER to simulate a box opening. The rest of the pipeline (Claude call, backend POST, email) runs for real.

---

## The classification states

| State | When | Feedback |
|---|---|---|
| **TOOK_PILL** | Patient reached for mouth, drank water, or visibly ingested a pill during the capture window | Green LED, short buzz, LCD "Great job!" |
| **NO_TAKE** | Patient was visible, upright, and conscious but never brought anything to their mouth | Red LED, long buzz, LCD "Please take your medicine" |
| **DISTRESS** | Patient collapsed, fell, clutched their chest, *or* was frozen in an abnormal posture for the full 15 seconds | Red LED, continuous buzz, LCD "Help coming — stay calm" |
| **NO_SHOW** | No person visible in any frame (patient may have opened the box and walked away) | LCD "Reminder: take pill now" |

---

## Design decisions worth calling out

**Batched over per-frame classification.** An earlier version sent 15 separate API calls and ran a majority vote. It missed pill-taking events all the time — 8 frames of "looking around" could outvote 7 frames of actual ingestion, even though the ingestion clearly happened. Switching to one API call with all 15 frames in order let Claude reason about the sequence as a narrative, and accuracy jumped immediately.

**Motion as a distress signal.** A calm, conscious person naturally shifts posture across 15 seconds. A person who is *frozen* in a head-tilted-back position for all 15 frames is almost certainly unconscious. The batched prompt explicitly asks Claude to treat lack of movement + abnormal posture as a hard distress signal.

**Reminder that can't be ignored.** The active-reminder mode flashes LEDs and pulses the buzzer on every poll iteration — not a discrete beep every 5 seconds. A deaf patient will see the lights from across the room; a patient with hearing will be annoyed into action. The reminder only stops when the physical sensor confirms the box was opened.

**Frames are auditable.** Every capture is archived with Claude's verdict alongside. If a classification is wrong, you can see exactly why.

---

## Roadmap

- Lid-edge detection (only trigger on closed→open transition, not continuous presence)
- Pi systemd service for autostart
- Video input instead of frames (once supported directly by the API)
- Per-pill recognition (is the *right* pill being taken at the right time?)
- Caretaker mobile app

---

*Built at a hackathon with a Pi, a pill box, and a lot of duct tape.* lol
