import json
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import get_patient, get_events_since, log_event, get_took_pill_count_since
from backend.alerts import send_event_alert, send_refill_alert

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
_refill_sent_this_week = False


def _check_no_show(patient_id, scheduled_time_str):
    """Called 30 minutes after a scheduled pill time to check if pill was taken."""
    patient = get_patient(patient_id)
    if not patient:
        return

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    window_start = f"{today} {scheduled_time_str}:00"
    window_end = (
        datetime.strptime(window_start, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=30)
    ).strftime("%Y-%m-%d %H:%M:%S")

    events = get_events_since(patient_id, window_start)
    took_pill = any(
        e["state"] == "TOOK_PILL" and e["timestamp"] <= window_end for e in events
    )

    if not took_pill:
        log_event(patient_id, "NO_SHOW", None, f"Missed scheduled {scheduled_time_str} dose")
        send_event_alert(
            patient["name"],
            patient.get("caretaker_phone", ""),
            "NO_SHOW",
        )
        logger.info(f"NO_SHOW logged for patient {patient_id} at {scheduled_time_str}")


def _check_refill(patient_id):
    """Check if refill alert should be sent."""
    global _refill_sent_this_week

    if _refill_sent_this_week:
        return

    patient = get_patient(patient_id)
    if not patient:
        return

    now = datetime.now()
    # Last Monday 00:00
    days_since_monday = now.weekday()
    last_monday = (now - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    count = get_took_pill_count_since(patient_id, last_monday.strftime("%Y-%m-%d %H:%M:%S"))
    threshold = patient.get("weekly_pill_count", 14) - 2

    if count >= threshold:
        send_refill_alert(patient["name"], patient.get("caretaker_phone", ""))
        _refill_sent_this_week = True
        logger.info(f"Refill alert sent for patient {patient_id}")


def reset_refill_flag():
    """Reset refill flag every Monday."""
    global _refill_sent_this_week
    _refill_sent_this_week = False


def load_schedule(patient_id=1):
    """Load patient's pill schedule and create APScheduler jobs."""
    # Remove existing no-show jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("noshow_") or job.id.startswith("refill_"):
            job.remove()

    patient = get_patient(patient_id)
    if not patient or not patient.get("pill_schedule"):
        return

    schedule = json.loads(patient["pill_schedule"]) if isinstance(patient["pill_schedule"], str) else patient["pill_schedule"]

    for entry in schedule:
        pill_time = entry["time"]  # "08:00"
        hour, minute = map(int, pill_time.split(":"))

        # Schedule check 30 minutes after pill time
        check_minute = minute + 30
        check_hour = hour
        if check_minute >= 60:
            check_minute -= 60
            check_hour += 1
        if check_hour >= 24:
            check_hour -= 24

        job_id = f"noshow_{patient_id}_{pill_time}"
        scheduler.add_job(
            _check_no_show,
            "cron",
            hour=check_hour,
            minute=check_minute,
            args=[patient_id, pill_time],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled no-show check for {pill_time} at {check_hour:02d}:{check_minute:02d}")

    # Refill check runs daily at noon
    scheduler.add_job(
        _check_refill,
        "cron",
        hour=12,
        minute=0,
        args=[patient_id],
        id=f"refill_{patient_id}",
        replace_existing=True,
    )

    # Reset refill flag every Monday at midnight
    scheduler.add_job(
        reset_refill_flag,
        "cron",
        day_of_week="mon",
        hour=0,
        minute=0,
        id="refill_reset",
        replace_existing=True,
    )


def start_scheduler(patient_id=1):
    load_schedule(patient_id)
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
