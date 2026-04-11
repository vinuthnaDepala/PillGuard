import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pi.claude_vision import classify_frame, final_classification
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


def buzz(duration=0.5):
    if HAS_GPIO:
        GPIO.output(BUZZER_PIN, True)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, False)
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

def is_within_pill_window():
    """Check if current time is within ±30 min of any scheduled pill time."""
    try:
        resp = requests.get(f"{BACKEND_URL}/patient/{PATIENT_ID}", timeout=5)
        patient = resp.json()
        schedule = patient.get("pill_schedule", [])
        if isinstance(schedule, str):
            schedule = json.loads(schedule)

        now = datetime.now()
        for entry in schedule:
            pill_time = datetime.strptime(entry["time"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            diff = abs((now - pill_time).total_seconds())
            if diff <= 1800:  # 30 minutes
                return True
        return False
    except Exception as e:
        logger.error(f"Failed to check schedule: {e}")
        return True  # Default to scheduled if we can't check


# --- Camera Capture ---

def capture_frames(simulate=False, test_image=None):
    """Capture 9 frames over 45 seconds (one every 5 seconds)."""
    frames = []

    if simulate:
        logger.info("Simulation mode: using test image for all frames")
        for i in range(9):
            frame_path = test_image or os.path.join(os.path.dirname(__file__), "test_frame.jpg")
            if os.path.exists(frame_path):
                frames.append(frame_path)
            else:
                logger.warning(f"Test image not found: {frame_path}")
            if i < 8:
                time.sleep(1)  # Shorter delay in simulation
        return frames

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            logger.error("Failed to open webcam")
            return frames

        for i in range(9):
            ret, frame = cap.read()
            if ret:
                path = f"/tmp/frame_{i}.jpg"
                cv2.imwrite(path, frame)
                frames.append(path)
                logger.info(f"Captured frame {i + 1}/9")
            else:
                logger.warning(f"Failed to capture frame {i + 1}")

            if i < 8:
                time.sleep(5)

        cap.release()
    except ImportError:
        logger.error("OpenCV not installed — cannot capture frames")

    return frames


def cleanup_frames(frames):
    for path in frames:
        if path.startswith("/tmp/") and os.path.exists(path):
            os.remove(path)


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
    logger.info(f"PillGuard starting (simulate={simulate})")
    lcd_display("idle")

    last_trigger_time = 0
    trigger_readings = []

    try:
        while True:
            if simulate:
                input("\n[SIM] Press ENTER to simulate box opening...")
                triggered = True
            else:
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
            unscheduled = not is_within_pill_window()

            if unscheduled:
                logger.info("Unscheduled box opening detected")
            else:
                logger.info("Scheduled pill window — box opened")

            lcd_display("pill_time")

            # Capture and classify frames
            frames = capture_frames(simulate=simulate, test_image=test_image)
            logger.info(f"Captured {len(frames)} frames, classifying...")

            results = []
            for frame_path in frames:
                result = classify_frame(frame_path)
                if result:
                    results.append(result)
                    logger.info(f"  Frame: {result['state']} ({result['confidence']})")

            # Final classification
            final = final_classification(results)
            state = final["state"]
            logger.info(f"Final classification: {state} (confidence: {final['confidence']})")

            # GPIO feedback
            handle_result(state)

            # LCD update
            lcd_display(state)

            # Post to backend
            post_event(state, final["confidence"], final["reason"], unscheduled)

            # Cleanup temp frames
            cleanup_frames(frames)

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
