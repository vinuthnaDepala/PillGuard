import os
import smtplib
import ssl
import logging
from email.message import EmailMessage
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

SUBJECTS = {
    "TOOK_PILL": "PillGuard: Medication taken",
    "NO_TAKE": "PillGuard: Medication NOT taken",
    "DISTRESS": "PillGuard: URGENT — Possible fall detected",
    "NO_SHOW": "PillGuard: Missed medication",
    "UNSCHEDULED": "PillGuard: Unscheduled box interaction",
    "REFILL": "PillGuard: Refill reminder",
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


def send_email(to_email, subject, body):
    """Send an email via SMTP (Gmail by default)."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_pass or not to_email:
        logger.warning("Email credentials not configured, email disabled")
        logger.info(f"EMAIL (not sent) to {to_email}: {subject} — {body}")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_event_alert(patient_name, caretaker_phone, state, unscheduled=False, caretaker_email=None):
    now = datetime.now().strftime("%I:%M %p")

    if unscheduled and state != "DISTRESS":
        key = "UNSCHEDULED"
    else:
        key = state

    template = TEMPLATES.get(key)
    if not template:
        return

    body = template.format(name=patient_name, time=now)
    subject = SUBJECTS.get(key, "PillGuard Alert")

    if caretaker_phone:
        send_sms(caretaker_phone, body)
    if caretaker_email:
        send_email(caretaker_email, subject, body)


def send_refill_alert(patient_name, caretaker_phone, caretaker_email=None):
    body = TEMPLATES["REFILL"].format(name=patient_name)
    subject = SUBJECTS["REFILL"]
    if caretaker_phone:
        send_sms(caretaker_phone, body)
    if caretaker_email:
        send_email(caretaker_email, subject, body)
