import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

TEMPLATES = {
    "TOOK_PILL": "\u2705 {name} took their {time} medication.",
    "NO_TAKE": "\u26a0\ufe0f {name} opened pill box but did not take medication.",
    "DISTRESS": "\ud83c\udd98 ALERT: Possible fall detected for {name}. Check immediately.",
    "NO_SHOW": "\u23f0 {name} missed their {time} medication \u2014 did not approach dispenser.",
    "UNSCHEDULED": "\u2139\ufe0f {name} interacted with pill box at unscheduled time ({time}).",
    "REFILL": "\ud83d\udc8a {name}'s weekly pill supply is running low. Please refill.",
}


def _get_twilio_client():
    try:
        from twilio.rest import Client

        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if not sid or not token or sid == "your_sid":
            logger.warning("Twilio credentials not configured, SMS disabled")
            return None
        return Client(sid, token)
    except ImportError:
        logger.warning("twilio package not installed, SMS disabled")
        return None


def send_sms(to_number, body):
    client = _get_twilio_client()
    if not client:
        logger.info(f"SMS (not sent): {body}")
        return False

    from_number = os.getenv("TWILIO_FROM_NUMBER")
    try:
        client.messages.create(body=body, from_=from_number, to=to_number)
        logger.info(f"SMS sent to {to_number}")
        return True
    except Exception as e:
        logger.error(f"Twilio SMS failed: {e}")
        return False


def send_event_alert(patient_name, caretaker_phone, state, unscheduled=False):
    now = datetime.now().strftime("%I:%M %p")

    if unscheduled and state != "DISTRESS":
        template = TEMPLATES["UNSCHEDULED"]
    else:
        template = TEMPLATES.get(state)

    if not template:
        return

    body = template.format(name=patient_name, time=now)
    send_sms(caretaker_phone, body)


def send_refill_alert(patient_name, caretaker_phone):
    body = TEMPLATES["REFILL"].format(name=patient_name)
    send_sms(caretaker_phone, body)
