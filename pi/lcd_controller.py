import logging
import time

logger = logging.getLogger(__name__)

# --- Grove RGB LCD driver (address 0x3e for text, 0x62 for RGB backlight) ---
_hardware = False
_bus = None

try:
    import smbus2
    _bus = smbus2.SMBus(1)
    _hardware = True
except ImportError:
    try:
        import smbus
        _bus = smbus.SMBus(1)
        _hardware = True
    except (ImportError, Exception) as e:
        logger.info(f"LCD hardware not available ({e}), using console output")

LCD_ADDR = 0x3e
RGB_ADDR = 0x62


def _send_command(cmd):
    _bus.write_byte_data(LCD_ADDR, 0x80, cmd)
    time.sleep(0.005)


def _send_data(data):
    _bus.write_byte_data(LCD_ADDR, 0x40, data)
    time.sleep(0.005)


def _set_rgb(r, g, b):
    _bus.write_byte_data(RGB_ADDR, 0x00, 0x00)  # mode1
    _bus.write_byte_data(RGB_ADDR, 0x01, 0x00)  # mode2
    _bus.write_byte_data(RGB_ADDR, 0x08, 0xAA)  # all LED control
    _bus.write_byte_data(RGB_ADDR, 0x04, r)      # red
    _bus.write_byte_data(RGB_ADDR, 0x03, g)      # green
    _bus.write_byte_data(RGB_ADDR, 0x02, b)      # blue


def _init_lcd():
    time.sleep(0.05)
    _send_command(0x28)  # 2 lines, 5x8
    _send_command(0x0C)  # display on, cursor off
    _send_command(0x01)  # clear
    time.sleep(0.005)
    _send_command(0x06)  # entry mode: left to right
    _set_rgb(255, 255, 255)  # white backlight


if _hardware and _bus:
    try:
        _init_lcd()
        logger.info("Grove RGB LCD initialized")
    except Exception as e:
        logger.info(f"LCD init failed ({e}), using console output")
        _hardware = False


MESSAGES = {
    "idle":      ("PillGuard", "Ready"),
    "pill_time": ("Time to take", "your medicine!"),
    "TOOK_PILL": ("Great job!", "Pill logged"),
    "NO_TAKE":   ("Please take", "your medicine"),
    "DISTRESS":  ("Help coming", "Stay calm"),
    "NO_SHOW":   ("Reminder:", "Take pill now!"),
}

STATE_COLORS = {
    "idle":      (255, 255, 255),  # white
    "pill_time": (0, 100, 255),    # blue
    "TOOK_PILL": (0, 255, 0),      # green
    "NO_TAKE":   (255, 165, 0),    # orange
    "DISTRESS":  (255, 0, 0),      # red
    "NO_SHOW":   (128, 128, 128),  # grey
}


def display(state):
    """Display a message on the LCD based on state key."""
    lines = MESSAGES.get(state, ("PillGuard", state[:16]))
    line1, line2 = lines

    if _hardware and _bus:
        _send_command(0x01)  # clear
        time.sleep(0.005)
        _send_command(0x80)  # first line
        for ch in line1[:16]:
            _send_data(ord(ch))
        _send_command(0xC0)  # second line
        for ch in line2[:16]:
            _send_data(ord(ch))
        r, g, b = STATE_COLORS.get(state, (255, 255, 255))
        _set_rgb(r, g, b)
    else:
        print(f"[LCD] {line1}")
        print(f"[LCD] {line2}")


def clear():
    if _hardware and _bus:
        _send_command(0x01)
        _set_rgb(0, 0, 0)
    else:
        print("[LCD] (cleared)")
