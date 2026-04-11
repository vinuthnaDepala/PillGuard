import logging

logger = logging.getLogger(__name__)

# Try to import RPLCD for real hardware; fall back to print-based mock
try:
    from RPLCD.i2c import CharLCD
    _lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2)
    _hardware = True
except (ImportError, Exception) as e:
    logger.info(f"LCD hardware not available ({e}), using console output")
    _lcd = None
    _hardware = False

MESSAGES = {
    "idle":      ("PillGuard", "Ready"),
    "pill_time": ("Time to take", "your medicine!"),
    "TOOK_PILL": ("Great job!", "Pill logged"),
    "NO_TAKE":   ("Please take", "your medicine"),
    "DISTRESS":  ("Help coming", "Stay calm"),
    "NO_SHOW":   ("Reminder:", "Take pill now!"),
}


def display(state):
    """Display a message on the LCD based on state key."""
    lines = MESSAGES.get(state, ("PillGuard", state[:16]))
    line1, line2 = lines

    if _hardware and _lcd:
        _lcd.clear()
        _lcd.cursor_pos = (0, 0)
        _lcd.write_string(line1[:16])
        _lcd.cursor_pos = (1, 0)
        _lcd.write_string(line2[:16])
    else:
        print(f"[LCD] {line1}")
        print(f"[LCD] {line2}")


def clear():
    if _hardware and _lcd:
        _lcd.clear()
    else:
        print("[LCD] (cleared)")
