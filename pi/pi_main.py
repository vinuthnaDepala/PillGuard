import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pi.claude_vision import classify_sequence
from pi.lcd_controller import display as lcd_display

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- GPIO Setup (with fallback for non-Pi machines) ---
try:
    import RPi.GPIO as GPIO

    TRIG_PIN = 23
    ECHO_PIN = 24
    GREEN_LED = 17
    RED_LED = 27
    BUZZER_PIN = 22

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.setup(GREEN_LED, GPIO.OUT)
    GPIO.setup(RED_LED, GPIO.OUT)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    HAS_GPIO = True
except ImportError:
    logger.info("RPi.GPIO not available — GPIO calls will be simulated")
    HAS_GPIO = False

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
PATIENT_ID = 1
COOLDOWN_SECONDS = 60
TRIGGER_THRESHOLD = 15  # cm
BASELINE_DISTANCE = 30  # cm


# --- Sensor ---

def read_distance():
    """Read distance from HC-SR04 sensor in cm."""
    if not HAS_GPIO:
        return BASELINE_DISTANCE

    GPIO.output(TRIG_PIN, False)
    time.sleep(0.05)
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    pulse_start = time.time()
    timeout = pulse_start + 0.04

    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
        if pulse_start > timeout:
            return -1

    pulse_end = time.time()
    timeout = pulse_end + 0.04

    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()
        if pulse_end > timeout:
            return -1

    duration = pulse_end - pulse_start
    distance = duration * 17150
    return round(distance, 2)


def is_valid_reading(distance):
    return 0 < distance < 400


# --- GPIO Control ---

def set_leds(green, red):
    if HAS_GPIO:
        GPIO.output(GREEN_LED, green)
        GPIO.output(RED_LED, red)
    else:
        g = "ON" if green else "OFF"
        r = "ON" if red else "OFF"
        print(f"[GPIO] Green LED: {g}, Red LED: {r}")


def buzz(duration=0.5, freq=1000):
    if HAS_GPIO:
        pwm = GPIO.PWM(BUZZER_PIN, freq)
        pwm.start(50)  # 50% duty cycle
        time.sleep(duration)
        pwm.stop()
    else:
        print(f"[GPIO] Buzzer: ON for {duration}s")


def handle_result(state):
    """Set LEDs and buzzer based on classification result."""
    if state == "TOOK_PILL":
        set_leds(green=True, red=False)
        buzz(0.2)
    elif state == "NO_TAKE":
        set_leds(green=False, red=True)
        buzz(0.5)
    elif state == "DISTRESS":
        set_leds(green=False, red=True)
        # Continuous buzzing for distress
        for _ in range(5):
            buzz(0.3)
            time.sleep(0.2)
    elif state == "NO_SHOW":
        set_leds(green=False, red=False)
    else:
        set_leds(green=False, red=False)


# --- Schedule Check ---

REMINDER_WINDOW_MINUTES = 30        # how long after pill time to keep reminding
REMINDER_BUZZ_INTERVAL = 5          # seconds between reminder buzzes
EARLY_WINDOW_MINUTES = 30           # how many minutes BEFORE scheduled time still counts as on-schedule

# Module state for reminder tracking
_handled_reminders = set()          # "YYYY-MM-DD HH:MM" strings that have been handled
_last_reminder_buzz = 0


def _fetch_schedule():
    """Fetch the patient's pill schedule from the backend."""
    try:
        resp = requests.get(f"{BACKEND_URL}/patient/{PATIENT_ID}", timeout=5)
        patient = resp.json()
        schedule = patient.get("pill_schedule", [])
        if isinstance(schedule, str):
            schedule = json.loads(schedule)
        return schedule
    except Exception as e:
        logger.error(f"Failed to fetch schedule: {e}")
        return []


def _fetch_recent_events(limit=20):
    """Fetch recent events from the backend."""
    try:
        resp = requests.get(f"{BACKEND_URL}/events/{PATIENT_ID}?limit={limit}", timeout=5)
        return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch events: {e}")
        return []


def is_within_pill_window():
    """Check if current time is within ±30 min of any scheduled pill time."""
    schedule = _fetch_schedule()
    if not schedule:
        return True  # Default to scheduled if we can't check

    now = datetime.now()
    for entry in schedule:
        pill_time = datetime.strptime(entry["time"], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        diff = abs((now - pill_time).total_seconds())
        if diff <= 1800:  # 30 minutes
            return True
    return False


def _parse_event_timestamp(ts_str):
    """Parse a timestamp string from the backend (SQLite CURRENT_TIMESTAMP format)."""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.fromisoformat(ts_str.replace("Z", ""))
        except Exception:
            return None


def _already_taken_for_slot(pill_time):
    """Check if a TOOK_PILL event already exists for this pill time slot.

    Slot window: [pill_time - EARLY_WINDOW_MINUTES, pill_time + REMINDER_WINDOW_MINUTES]
    """
    events = _fetch_recent_events(limit=30)
    window_start = pill_time - timedelta(minutes=EARLY_WINDOW_MINUTES)
    window_end = pill_time + timedelta(minutes=REMINDER_WINDOW_MINUTES)
    for e in events:
        if e.get("state") != "TOOK_PILL":
            continue
        ts = _parse_event_timestamp(e.get("timestamp", ""))
        if ts and window_start <= ts <= window_end:
            return True
    return False


def get_active_reminder():
    """Return the scheduled pill time ('HH:MM') that needs an active reminder, or None.

    A reminder is active when:
      - Current time is between scheduled time and scheduled + REMINDER_WINDOW_MINUTES
      - No TOOK_PILL event exists yet for this slot
      - The slot hasn't been marked as handled (box opened) yet this loop
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    schedule = _fetch_schedule()

    for entry in schedule:
        time_str = entry["time"]
        slot_key = f"{today_str} {time_str}"

        if slot_key in _handled_reminders:
            continue

        pill_time = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )

        # Only active from scheduled time until +REMINDER_WINDOW_MINUTES
        if pill_time <= now <= pill_time + timedelta(minutes=REMINDER_WINDOW_MINUTES):
            if _already_taken_for_slot(pill_time):
                _handled_reminders.add(slot_key)
                continue
            return time_str

    return None


def mark_current_reminder_handled():
    """Mark the currently-active reminder slot as handled (called when sensor triggers)."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    schedule = _fetch_schedule()

    for entry in schedule:
        time_str = entry["time"]
        pill_time = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if pill_time <= now <= pill_time + timedelta(minutes=REMINDER_WINDOW_MINUTES):
            slot_key = f"{today_str} {time_str}"
            _handled_reminders.add(slot_key)
            logger.info(f"Reminder for {time_str} marked as handled (sensor triggered)")
            return


# --- Camera Capture ---

NUM_FRAMES = 15
CAPTURE_DURATION_SECONDS = 15
FRAMES_ARCHIVE_DIR = os.path.expanduser("~/pillguard_frames")


def capture_frames(simulate=False, test_image=None):
    """Capture NUM_FRAMES frames over CAPTURE_DURATION_SECONDS seconds.
    Saves to a timestamped folder in ~/pillguard_frames/ so they can be reviewed later.
    Returns (frames_list, archive_dir).
    """
    frames = []
    interval = CAPTURE_DURATION_SECONDS / NUM_FRAMES

    # Create timestamped archive folder for this capture
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.join(FRAMES_ARCHIVE_DIR, timestamp)
    os.makedirs(archive_dir, exist_ok=True)
    logger.info(f"Saving frames to {archive_dir}")

    if simulate:
        logger.info("Simulation mode: using test image for all frames")
        for i in range(NUM_FRAMES):
            frame_path = test_image or os.path.join(os.path.dirname(__file__), "test_frame.jpg")
            if os.path.exists(frame_path):
                frames.append(frame_path)
            else:
                logger.warning(f"Test image not found: {frame_path}")
            if i < NUM_FRAMES - 1:
                time.sleep(1)  # Shorter delay in simulation
        return frames, archive_dir

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            logger.error("Failed to open webcam")
            return frames, archive_dir

        for i in range(NUM_FRAMES):
            ret, frame = cap.read()
            if ret:
                path = os.path.join(archive_dir, f"frame_{i:02d}.jpg")
                cv2.imwrite(path, frame)
                frames.append(path)
                logger.info(f"Captured frame {i + 1}/{NUM_FRAMES}")
            else:
                logger.warning(f"Failed to capture frame {i + 1}")

            if i < NUM_FRAMES - 1:
                time.sleep(interval)

        cap.release()
    except ImportError:
        logger.error("OpenCV not installed — cannot capture frames")

    return frames, archive_dir


def save_results_log(archive_dir, results, final):
    """Save classification results alongside the frames for review."""
    try:
        log_path = os.path.join(archive_dir, "results.json")
        with open(log_path, "w") as f:
            json.dump({"frame_results": results, "final": final}, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save results log: {e}")


# --- Backend POST ---

def post_event(state, confidence, reason, unscheduled=False):
    payload = {
        "patient_id": PATIENT_ID,
        "state": state,
        "confidence": confidence,
        "reason": reason,
        "unscheduled": unscheduled,
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/event", json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Event posted: {state}")
        else:
            logger.error(f"Backend returned {resp.status_code}: {resp.text}")
            _fallback_log(payload)
    except Exception as e:
        logger.error(f"Backend POST failed: {e}")
        _fallback_log(payload)


def _fallback_log(payload):
    """Log event locally if backend is unreachable."""
    with open("/tmp/pillguard_fallback.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} | {json.dumps(payload)}\n")
    logger.info("Event saved to fallback log")


# --- Main Loop ---

def run(simulate=False, test_image=None):
    global _last_reminder_buzz
    logger.info(f"PillGuard starting (simulate={simulate})")
    lcd_display("idle")

    last_trigger_time = 0
    trigger_readings = []
    reminder_active = False
    led_toggle = False

    try:
        while True:
            if simulate:
                input("\n[SIM] Press ENTER to simulate box opening...")
                triggered = True
            else:
                # --- Active reminder check (buzz + flash LEDs until sensor triggered) ---
                active_slot = get_active_reminder()
                if active_slot:
                    if not reminder_active:
                        logger.info(f"Reminder ACTIVE for {active_slot} — buzzing + flashing until box opens")
                        lcd_display("pill_time")
                        reminder_active = True
                    # Flash LEDs alternately so deaf patients get a visual signal
                    led_toggle = not led_toggle
                    set_leds(green=led_toggle, red=not led_toggle)
                    # Near-continuous buzzing — short pulse every loop iteration
                    buzz(0.2, freq=2000)
                else:
                    if reminder_active:
                        logger.info("Reminder cleared")
                        lcd_display("idle")
                        set_leds(green=False, red=False)
                        reminder_active = False
                        led_toggle = False

                distance = read_distance()
                if not is_valid_reading(distance):
                    time.sleep(0.5)
                    continue

                if distance < TRIGGER_THRESHOLD:
                    trigger_readings.append(distance)
                else:
                    trigger_readings.clear()

                if len(trigger_readings) >= 3:
                    elapsed = time.time() - last_trigger_time
                    triggered = elapsed >= COOLDOWN_SECONDS
                    trigger_readings.clear()
                else:
                    triggered = False

                if not triggered:
                    time.sleep(0.5)
                    continue

            # --- Triggered ---
            last_trigger_time = time.time()
            mark_current_reminder_handled()
            reminder_active = False
            unscheduled = not is_within_pill_window()

            if unscheduled:
                logger.info("Unscheduled box opening detected")
            else:
                logger.info("Scheduled pill window — box opened")

            lcd_display("pill_time")

            # Capture frames
            frames, archive_dir = capture_frames(simulate=simulate, test_image=test_image)
            logger.info(f"Captured {len(frames)} frames, sending to Claude as one batch...")

            # Single API call — Claude reasons about the whole sequence
            final = classify_sequence(frames)
            state = final["state"]
            logger.info(f"Final classification: {state} (confidence: {final['confidence']})")
            logger.info(f"Reason: {final['reason']}")

            # Save result alongside frames for review
            save_results_log(archive_dir, [], final)
            logger.info(f"Frames and results saved to {archive_dir}")

            # GPIO feedback
            handle_result(state)

            # LCD update
            lcd_display(state)

            # Post to backend
            post_event(state, final["confidence"], final["reason"], unscheduled)

            # Keep result display for 10 seconds then return to idle
            time.sleep(10)
            set_leds(green=False, red=False)
            lcd_display("idle")

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if HAS_GPIO:
            GPIO.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PillGuard Pi Controller")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode (no hardware)")
    parser.add_argument("--test-image", type=str, help="Path to test image for simulation mode")
    args = parser.parse_args()

    run(simulate=args.simulate, test_image=args.test_image)
