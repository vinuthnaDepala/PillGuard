import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pillguard.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            caretaker_name TEXT,
            caretaker_phone TEXT,
            caretaker_email TEXT,
            pill_schedule TEXT,
            weekly_pill_count INTEGER DEFAULT 14
        )
    """)

    # Migration: add caretaker_email column if it doesn't exist (for existing DBs)
    cursor.execute("PRAGMA table_info(patients)")
    cols = [row[1] for row in cursor.fetchall()]
    if "caretaker_email" not in cols:
        cursor.execute("ALTER TABLE patients ADD COLUMN caretaker_email TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            state TEXT NOT NULL,
            confidence REAL,
            reason TEXT,
            unscheduled INTEGER DEFAULT 0,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # Seed default patient if table is empty
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] == 0:
        default_schedule = json.dumps([{"time": "08:00"}, {"time": "20:00"}])
        cursor.execute(
            "INSERT INTO patients (id, name, caretaker_name, caretaker_phone, caretaker_email, pill_schedule, weekly_pill_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                "Eleanor",
                "Sarah",
                os.getenv("CARETAKER_PHONE", "+1xxxxxxxxxx"),
                os.getenv("CARETAKER_EMAIL", ""),
                default_schedule,
                14,
            ),
        )

    conn.commit()
    conn.close()


def log_event(patient_id, state, confidence, reason, unscheduled=False):
    conn = get_connection()
    conn.execute(
        "INSERT INTO events (patient_id, state, confidence, reason, unscheduled) VALUES (?, ?, ?, ?, ?)",
        (patient_id, state, confidence, reason, 1 if unscheduled else 0),
    )
    conn.commit()
    conn.close()


def get_events(patient_id, limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE patient_id = ? ORDER BY timestamp DESC LIMIT ?",
        (patient_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_patient(patient_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_patient_schedule(patient_id, pill_schedule, weekly_pill_count):
    conn = get_connection()
    conn.execute(
        "UPDATE patients SET pill_schedule = ?, weekly_pill_count = ? WHERE id = ?",
        (json.dumps(pill_schedule), weekly_pill_count, patient_id),
    )
    conn.commit()
    conn.close()


def update_patient(patient_id, name, caretaker_name, caretaker_phone, caretaker_email=None):
    conn = get_connection()
    conn.execute(
        "UPDATE patients SET name = ?, caretaker_name = ?, caretaker_phone = ?, caretaker_email = ? WHERE id = ?",
        (name, caretaker_name, caretaker_phone, caretaker_email, patient_id),
    )
    conn.commit()
    conn.close()


def get_events_since(patient_id, since_timestamp):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE patient_id = ? AND timestamp >= ? ORDER BY timestamp DESC",
        (patient_id, since_timestamp),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_took_pill_count_since(patient_id, since_timestamp):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM events WHERE patient_id = ? AND state = 'TOOK_PILL' AND timestamp >= ?",
        (patient_id, since_timestamp),
    ).fetchone()
    conn.close()
    return row[0]


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
