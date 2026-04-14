"""Standalone test for the pill-box sensor logic.

Shows the full state machine live:
  - Raw distance reading
  - Debounce buffer (consecutive under-threshold readings)
  - Cooldown state
  - Trigger events

Run on the Pi:
    cd ~/pillguard
    source .venv/bin/activate
    python -m pi.sensor_test

Press Ctrl+C to stop.
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    print("RPi.GPIO not available — this test must run on a Pi")
    sys.exit(1)

# --- Config (same as pi_main.py) ---
TRIG_PIN = 23
ECHO_PIN = 24
TRIGGER_THRESHOLD = 15   # cm — below this = "lid open"
DEBOUNCE_COUNT = 3       # consecutive readings needed to trigger
COOLDOWN_SECONDS = 60    # ignore re-triggers for this long
POLL_INTERVAL = 0.5      # seconds between readings

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)


def read_distance():
    """One HC-SR04 ping. Returns cm, or -1 on timeout."""
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

    return round((pulse_end - pulse_start) * 17150, 1)


def is_valid_reading(d):
    return 0 < d < 400


def main():
    print("=" * 70)
    print("PILLGUARD SENSOR STATE MACHINE TEST")
    print("=" * 70)
    print(f"  TRIGGER_THRESHOLD:  {TRIGGER_THRESHOLD} cm  (distance below this = lid open)")
    print(f"  DEBOUNCE_COUNT:     {DEBOUNCE_COUNT} consecutive readings")
    print(f"  COOLDOWN_SECONDS:   {COOLDOWN_SECONDS}s after a trigger")
    print(f"  POLL_INTERVAL:      {POLL_INTERVAL}s")
    print()
    print("What to try:")
    print("  1. Leave the box alone to see the baseline distance")
    print("  2. Put your hand in front of the sensor — watch the buffer fill")
    print("  3. Keep it there until you see TRIGGER FIRED")
    print("  4. Immediately try again — cooldown should block it")
    print("  5. Wave your hand in/out quickly — debounce should prevent false triggers")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 70)

    trigger_readings = []
    last_trigger_time = 0
    trigger_count = 0
    tick = 0

    try:
        while True:
            tick += 1
            distance = read_distance()
            now = time.time()

            # Cooldown status
            in_cooldown = (now - last_trigger_time) < COOLDOWN_SECONDS
            cooldown_remaining = max(0, COOLDOWN_SECONDS - (now - last_trigger_time))

            # Validate reading
            if not is_valid_reading(distance):
                status = "INVALID (discarded)"
                buffer_str = "-"
                fired = False
            else:
                # Debounce logic
                if distance < TRIGGER_THRESHOLD:
                    trigger_readings.append(distance)
                else:
                    if trigger_readings:
                        trigger_readings.clear()

                buffer_str = f"[{','.join(f'{d:.1f}' for d in trigger_readings)}]" if trigger_readings else "[]"

                fired = False
                if len(trigger_readings) >= DEBOUNCE_COUNT:
                    if not in_cooldown:
                        trigger_count += 1
                        last_trigger_time = now
                        fired = True
                    trigger_readings.clear()

                if distance < TRIGGER_THRESHOLD:
                    status = "*** UNDER THRESHOLD ***"
                else:
                    status = "idle (above threshold)"

            # Build the live line
            cooldown_str = f"COOLDOWN {cooldown_remaining:4.1f}s" if in_cooldown else "ready       "

            line = (
                f"t={tick:4d}  "
                f"d={distance:6.1f}cm  "
                f"buf={buffer_str:<20}  "
                f"{cooldown_str}  "
                f"{status}"
            )
            print(line)

            if fired:
                print()
                print("=" * 70)
                print(f"  🔔 TRIGGER FIRED #{trigger_count}")
                print(f"  Would now start 15-second webcam capture + Claude classification")
                print(f"  Cooldown starts now ({COOLDOWN_SECONDS}s)")
                print("=" * 70)
                print()

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print()
        print("-" * 70)
        print(f"Stopped. Total triggers fired: {trigger_count}")
        GPIO.cleanup()


if __name__ == "__main__":
    main()
