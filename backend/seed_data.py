"""
Task 1 — Sample data for the Vehicle Booking and Usage Register.

Field dictionary
-----------------
booking_id    : text, format BK-0001. Auto-assigned by the server, never
                 entered by hand.
vehicle_no    : text, e.g. TN22AB1234. The institution's vehicle registration
                 number. Stored uppercase, no spaces.
requested_by  : text. Name of the staff/faculty member requesting the vehicle.
department    : text. The department that will be charged for the trip
                 (e.g. Administration, AIDS, Mechanical, Sports).
journey_date  : date, YYYY-MM-DD. The date the vehicle is required.
start_time    : time, HH:MM (24-hour). When the vehicle is required from.
end_time      : time, HH:MM (24-hour). When the vehicle is expected back.
purpose       : text. Short reason for the trip (e.g. "Guest pickup - airport").
km_used       : number or null. Distance covered, filled in ONLY after the
                 trip is completed. Null/blank means "not yet recorded", not
                 zero — a pending or in-progress booking has no km yet.
status        : one of pending / confirmed / completed / cancelled.

Deliberately awkward records included (and why):
  - BK-0015: km_used is missing even though status is "completed" -> forces
    a decision on what the usage screen shows when a number can't be
    calculated (we show the trip in trip_count but exclude it from the km
    total, and surface a missing_km_count instead of pretending it's 0).
  - BK-0016 vs BK-0017: two very similar requester names ("Aravind S" and
    "Aravind S.") on different departments -> tests that search/aggregation
    doesn't accidentally merge or split them.
  - BK-0040: a record with almost nothing useful in it (placeholder purpose,
    department "Unassigned") -> tests that the register still displays it
    without crashing or leaving a blank row.
"""

import random
import sqlite3
from datetime import date, timedelta

from app import init_db, DB_PATH

random.seed(42)

VEHICLES = ["TN22AB1234", "TN22AC5678", "TN22AD9012", "TN22AE3456"]
DEPARTMENTS = ["AIDS", "Mechanical", "Administration", "Sports", "Civil", "Physics"]
PURPOSES = [
    "Guest pickup - airport", "Inter-college sports meet", "Material collection - vendor",
    "Faculty conference travel", "Student excursion", "Lab equipment transport",
    "Placement drive - company visit", "Hospital emergency drop", "Exam paper collection",
]
NAMES = [
    "R. Karthik", "S. Priya", "M. Suresh", "Aravind S", "Aravind S.",
    "K. Meena", "T. Bala", "N. Deepa", "V. Ramesh", "P. Anitha",
]

rows = []
today = date(2026, 7, 27)

for i in range(1, 41):
    booking_id = f"BK-{i:04d}"
    vehicle = random.choice(VEHICLES)
    requester = random.choice(NAMES)
    dept = random.choice(DEPARTMENTS)
    jdate = today - timedelta(days=random.randint(1, 30))
    start_h = random.randint(7, 16)
    start = f"{start_h:02d}:00"
    end = f"{start_h + random.randint(1, 3):02d}:{random.choice(['00','30'])}"
    purpose = random.choice(PURPOSES)
    status = random.choice(["completed", "completed", "confirmed", "pending"])
    km = round(random.uniform(8, 120), 1) if status == "completed" else None

    rows.append({
        "booking_id": booking_id, "vehicle_no": vehicle, "requested_by": requester,
        "department": dept, "journey_date": jdate.isoformat(), "start_time": start,
        "end_time": end, "purpose": purpose, "km_used": km, "status": status,
        "client_ref": f"seed-{booking_id}",
    })

# --- deliberate awkward cases, overriding a few generated rows ---
rows[14].update({  # BK-0015: completed trip, km_used missing
    "status": "completed", "km_used": None, "purpose": "Faculty conference travel",
})
rows[15].update({"requested_by": "Aravind S", "department": "AIDS"})       # BK-0016
rows[16].update({"requested_by": "Aravind S.", "department": "Mechanical"})  # BK-0017
rows[39].update({  # BK-0040: barely-there record
    "requested_by": "N/A", "department": "Unassigned", "purpose": "misc",
    "km_used": None, "status": "pending",
})


def seed():
    init_db()
    db = sqlite3.connect(DB_PATH)
    db.execute("DELETE FROM bookings")
    for r in rows:
        db.execute(
            """
            INSERT INTO bookings
            (booking_id, vehicle_no, requested_by, department, journey_date,
             start_time, end_time, purpose, km_used, status, client_ref)
            VALUES (:booking_id, :vehicle_no, :requested_by, :department,
                    :journey_date, :start_time, :end_time, :purpose, :km_used,
                    :status, :client_ref)
            """,
            r,
        )
    db.commit()
    db.close()
    print(f"Seeded {len(rows)} bookings into {DB_PATH}")


if __name__ == "__main__":
    seed()
