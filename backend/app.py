"""
Institutional Vehicle Booking and Usage Register — backend
Flask + SQLite. All validation and all derived-figure calculation
happens here, on the server, so every screen shows the same number.
"""

import os
import sqlite3
from datetime import datetime, date
from flask import Flask, request, jsonify, g
from flask_cors import CORS

DB_PATH = os.environ.get("DB_PATH", "register.db")

app = Flask(__name__)
CORS(app)

VALID_STATUSES = {"pending", "confirmed", "completed", "cancelled"}
REQUIRED_FIELDS = [
    "vehicle_no", "requested_by", "department",
    "journey_date", "start_time", "end_time", "purpose",
]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id   TEXT PRIMARY KEY,
            vehicle_no   TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            department   TEXT NOT NULL,
            journey_date TEXT NOT NULL,
            start_time   TEXT NOT NULL,
            end_time     TEXT NOT NULL,
            purpose      TEXT NOT NULL,
            km_used      REAL,
            status       TEXT NOT NULL,
            client_ref   TEXT UNIQUE
        )
        """
    )
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def validate_payload(data):
    """Returns (cleaned_data, error_message). error_message is None if valid."""
    cleaned = {}

    for field in REQUIRED_FIELDS:
        val = (data.get(field) or "").strip() if isinstance(data.get(field), str) else data.get(field)
        if val in (None, ""):
            return None, f"'{field}' is required."
        cleaned[field] = val

    try:
        jdate = parse_date(cleaned["journey_date"])
    except (ValueError, TypeError):
        return None, "journey_date must be in YYYY-MM-DD format."
    if jdate < date.today():
        # allow past dates only for historical/seed data via a flag
        if not data.get("allow_past"):
            return None, "journey_date cannot be in the past."

    try:
        start_t = parse_time(cleaned["start_time"])
        end_t = parse_time(cleaned["end_time"])
    except (ValueError, TypeError):
        return None, "start_time / end_time must be in HH:MM format."

    if end_t <= start_t:
        return None, "end_time must be after start_time."

    cleaned["vehicle_no"] = cleaned["vehicle_no"].upper().replace(" ", "")

    status = (data.get("status") or "pending").strip().lower()
    if status not in VALID_STATUSES:
        return None, f"status must be one of {sorted(VALID_STATUSES)}."
    cleaned["status"] = status

    km_used = data.get("km_used")
    if km_used in (None, ""):
        cleaned["km_used"] = None
    else:
        try:
            km_used = float(km_used)
        except (ValueError, TypeError):
            return None, "km_used must be a number."
        if km_used < 0:
            return None, "km_used cannot be negative."
        cleaned["km_used"] = km_used

    cleaned["journey_date"] = cleaned["journey_date"]
    cleaned["client_ref"] = data.get("client_ref")  # used for offline dedupe
    return cleaned, None


def overlapping_booking(db, vehicle_no, journey_date, start_time, end_time, exclude_id=None):
    """Server-side double-booking check: same vehicle, same date, overlapping time window."""
    q = """
        SELECT booking_id, requested_by, start_time, end_time FROM bookings
        WHERE vehicle_no = ? AND journey_date = ? AND status != 'cancelled'
        AND NOT (end_time <= ? OR start_time >= ?)
    """
    params = [vehicle_no, journey_date, start_time, end_time]
    if exclude_id:
        q += " AND booking_id != ?"
        params.append(exclude_id)
    return db.execute(q, params).fetchone()


def next_booking_id(db):
    row = db.execute("SELECT booking_id FROM bookings ORDER BY rowid DESC LIMIT 1").fetchone()
    if not row:
        return "BK-0001"
    last_num = int(row["booking_id"].split("-")[1])
    return f"BK-{last_num + 1:04d}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/bookings", methods=["GET"])
def list_bookings():
    db = get_db()
    vehicle = request.args.get("vehicle_no")
    department = request.args.get("department")
    q = "SELECT * FROM bookings WHERE 1=1"
    params = []
    if vehicle:
        q += " AND vehicle_no = ?"
        params.append(vehicle.upper())
    if department:
        q += " AND department = ?"
        params.append(department)
    q += " ORDER BY journey_date DESC, start_time DESC"
    rows = db.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json(force=True, silent=True) or {}
    db = get_db()

    # Idempotency: if this exact client_ref was already submitted (e.g. a
    # retry after reconnecting from offline mode), return the existing
    # record instead of creating a duplicate.
    client_ref = data.get("client_ref")
    if client_ref:
        existing = db.execute(
            "SELECT * FROM bookings WHERE client_ref = ?", (client_ref,)
        ).fetchone()
        if existing:
            return jsonify(dict(existing)), 200

    cleaned, err = validate_payload(data)
    if err:
        return jsonify({"error": err}), 400

    clash = overlapping_booking(
        db, cleaned["vehicle_no"], cleaned["journey_date"],
        cleaned["start_time"], cleaned["end_time"],
    )
    if clash:
        return jsonify({
            "error": (
                f"Vehicle {cleaned['vehicle_no']} is already booked on "
                f"{cleaned['journey_date']} from {clash['start_time']} to "
                f"{clash['end_time']} (booking {clash['booking_id']}, "
                f"requested by {clash['requested_by']})."
            )
        }), 409

    booking_id = next_booking_id(db)
    db.execute(
        """
        INSERT INTO bookings
        (booking_id, vehicle_no, requested_by, department, journey_date,
         start_time, end_time, purpose, km_used, status, client_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            booking_id, cleaned["vehicle_no"], cleaned["requested_by"],
            cleaned["department"], cleaned["journey_date"],
            cleaned["start_time"], cleaned["end_time"], cleaned["purpose"],
            cleaned["km_used"], cleaned["status"], cleaned["client_ref"],
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/usage", methods=["GET"])
def usage_by_department():
    """Derived figure: total km_used and trip count per department.
    Bookings with no km_used recorded yet are counted as trips but
    excluded from the km total (and reported separately) instead of
    silently treated as zero.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT department,
               COUNT(*) AS trip_count,
               SUM(CASE WHEN km_used IS NOT NULL THEN km_used ELSE 0 END) AS total_km,
               SUM(CASE WHEN km_used IS NULL THEN 1 ELSE 0 END) AS missing_km_count
        FROM bookings
        WHERE status != 'cancelled'
        GROUP BY department
        ORDER BY total_km DESC
        """
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/usage/vehicles", methods=["GET"])
def usage_by_vehicle():
    db = get_db()
    rows = db.execute(
        """
        SELECT vehicle_no,
               COUNT(*) AS trip_count,
               SUM(CASE WHEN km_used IS NOT NULL THEN km_used ELSE 0 END) AS total_km,
               SUM(CASE WHEN km_used IS NULL THEN 1 ELSE 0 END) AS missing_km_count
        FROM bookings
        WHERE status != 'cancelled'
        GROUP BY vehicle_no
        ORDER BY vehicle_no
        """
    ).fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG", "0") == "1")
else:
    init_db()
