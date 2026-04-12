import json
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from backend.database import (
    init_db,
    log_event,
    get_events,
    get_patient,
    update_patient_schedule,
    update_patient,
    get_events_since,
    get_took_pill_count_since,
)
from backend.alerts import send_event_alert
from backend.scheduler import start_scheduler, load_schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    logger.info("PillGuard backend started")
    yield
    logger.info("PillGuard backend shutting down")


app = FastAPI(title="PillGuard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---


class EventRequest(BaseModel):
    patient_id: int
    state: str
    confidence: Optional[float] = None
    reason: Optional[str] = None
    unscheduled: bool = False


class ScheduleUpdate(BaseModel):
    pill_schedule: list
    weekly_pill_count: int


class PatientUpdate(BaseModel):
    name: str
    caretaker_name: Optional[str] = None
    caretaker_phone: Optional[str] = None
    caretaker_email: Optional[str] = None


# --- Endpoints ---


@app.post("/event")
def create_event(req: EventRequest):
    patient = get_patient(req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    log_event(req.patient_id, req.state, req.confidence, req.reason, req.unscheduled)

    # Send SMS + email alert (don't block on failure)
    try:
        send_event_alert(
            patient["name"],
            patient.get("caretaker_phone", ""),
            req.state,
            req.unscheduled,
            caretaker_email=patient.get("caretaker_email") or os.getenv("CARETAKER_EMAIL"),
        )
    except Exception as e:
        logger.error(f"Alert failed: {e}")

    return {"status": "ok"}


@app.get("/events/{patient_id}")
def read_events(patient_id: int, limit: int = 50):
    events = get_events(patient_id, limit)
    return events


@app.get("/patient/{patient_id}")
def read_patient(patient_id: int):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Parse pill_schedule from JSON string
    if patient.get("pill_schedule") and isinstance(patient["pill_schedule"], str):
        patient["pill_schedule"] = json.loads(patient["pill_schedule"])
    return patient


@app.put("/patient/{patient_id}/schedule")
def update_schedule(patient_id: int, req: ScheduleUpdate):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_patient_schedule(patient_id, req.pill_schedule, req.weekly_pill_count)
    load_schedule(patient_id)
    return {"status": "ok"}


@app.put("/patient/{patient_id}")
def update_patient_info(patient_id: int, req: PatientUpdate):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_patient(patient_id, req.name, req.caretaker_name, req.caretaker_phone, req.caretaker_email)
    return {"status": "ok"}


@app.get("/stats/{patient_id}")
def read_stats(patient_id: int):
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    schedule = patient.get("pill_schedule", "[]")
    if isinstance(schedule, str):
        schedule = json.loads(schedule)
    daily_expected = len(schedule)

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Today's stats
    today_events = get_events_since(patient_id, f"{today_str} 00:00:00")
    today_taken = sum(1 for e in today_events if e["state"] == "TOOK_PILL")
    today_missed = sum(1 for e in today_events if e["state"] == "NO_SHOW")

    # Week adherence (last 7 days)
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    week_events = get_events_since(patient_id, week_start)
    week_taken = sum(1 for e in week_events if e["state"] == "TOOK_PILL")
    week_expected = daily_expected * 7
    week_adherence_pct = round((week_taken / week_expected * 100) if week_expected > 0 else 0, 1)

    # Month adherence (last 30 days)
    month_start = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    month_events = get_events_since(patient_id, month_start)
    month_taken = sum(1 for e in month_events if e["state"] == "TOOK_PILL")
    month_expected = daily_expected * 30
    month_adherence_pct = round((month_taken / month_expected * 100) if month_expected > 0 else 0, 1)

    # Daily adherence for last 30 days
    daily_adherence = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i))
        day_str = day.strftime("%Y-%m-%d")
        day_events = get_events_since(patient_id, f"{day_str} 00:00:00")
        # Filter to only this day
        day_events = [
            e for e in day_events
            if e["timestamp"].startswith(day_str)
        ]
        day_taken = sum(1 for e in day_events if e["state"] == "TOOK_PILL")
        pct = round((day_taken / daily_expected) if daily_expected > 0 else 0, 2)
        daily_adherence.append({"date": day_str, "pct": pct})

    return {
        "today_taken": today_taken,
        "today_missed": today_missed,
        "week_adherence_pct": week_adherence_pct,
        "month_adherence_pct": month_adherence_pct,
        "daily_adherence": daily_adherence,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
