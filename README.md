# Institutional Vehicle Booking and Usage Register

A small register that replaces the transport office's phone-and-diary
booking system. It stops double bookings automatically and shows which
department is using each vehicle and how much.

## What's in here

```
backend/                      Flask + SQLite API (validation, double-booking check, usage aggregation)
frontend/                     Single-page HTML/CSS/JS app: capture screen, register, usage dashboard
.github/workflows/main.yml    GitHub Actions CI workflow (Docker build and seed test)
docker-compose.yml            Docker orchestration configuration
gen_pdf.py                    Python automation script to generate the presentation
presentation.pdf              Completed presentation (6-8 slides covering implementation details)
```

## Running it locally (no Docker)

```bash
cd backend
pip install -r requirements.txt
python3 seed_data.py      # loads the 40-record sample dataset
python3 app.py            # starts the API on http://localhost:5000
```

Then open `frontend/index.html` in a browser (or serve it with
`python3 -m http.server 8080` from inside `frontend/`).

## Running it with Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- API: http://localhost:5000
- Frontend: http://localhost:8080

The database lives in a Docker volume (`register_data`), so it survives
container restarts. Sample data is seeded automatically the first time the
backend container starts with an empty database.

## What each field means

| Field | Meaning |
|---|---|
| `booking_id` | Auto-assigned, e.g. `BK-0041`. Never entered by hand. |
| `vehicle_no` | The vehicle's registration number. Stored uppercase, no spaces. |
| `requested_by` | Name of the staff/faculty member requesting the vehicle. |
| `department` | The department that will be charged for the trip. |
| `journey_date` | Date the vehicle is required (`YYYY-MM-DD`). |
| `start_time` / `end_time` | 24-hour time the vehicle is required from / expected back. |
| `purpose` | Short reason for the trip. |
| `km_used` | Distance covered. **Blank means "not yet recorded"**, not zero — it's filled in only after a trip completes. |
| `status` | `pending`, `confirmed`, `completed`, or `cancelled`. |

## How the double-booking check works

Before saving a new booking, the server looks for any other non-cancelled
booking for the **same vehicle** on the **same date** whose time range
overlaps the new one, and rejects the request with the clashing booking's
ID and requester so the clerk can resolve it on the spot. This happens
server-side only, so the clerk always sees the true state — never a stale
copy from another tab or device.

## How the usage figure is calculated

For each department: `total_km` = the sum of `km_used` across all
non-cancelled bookings for that department, and `trip_count` = the number
of such bookings. Trips with no `km_used` recorded yet are **counted in
`trip_count` but excluded from `total_km`**, and reported separately as
`missing_km_count` — so a department's total never silently understates or
fabricates a number it doesn't actually have yet.

Hand-checked example (from the seed data): the AIDS department has 4
bookings with a recorded distance (88.2 + 75.1 + 89.0 + 12.7 = **265.0 km**)
and 1 further completed trip with no distance recorded yet. The API
reports `total_km: 265.0`, `trip_count: 5`, `missing_km_count: 1` —
matching the hand calculation exactly.

## Offline behaviour (tested per Task 5)

The capture screen keeps working with no network: a submitted booking that
can't reach the server is stored in the browser's local storage and marked
as saved-locally; a status indicator in the header shows "offline · N saved
locally". 

To ensure full clarity, **offline queued bookings are displayed immediately in the Register table** with `(pending)` as their ID and their status set to `pending`. They are fully searchable even while offline. 

Once the connection returns, queued bookings are sent automatically. Each booking carries a `client_ref` generated on the device; the server treats a repeated `client_ref` as the same booking and returns the original record instead of creating a duplicate, so a retry after reconnecting never double-books.

## Known limitations / what's unfinished

- No authentication — anyone with the URL can book on behalf of any
  department. Fine for an internal single-office tool at this stage, not
  for a shared deployment.
- The vehicle list in the capture form is hardcoded to the four sample
  vehicles rather than pulled from a vehicles table.
- No edit/cancel action from the register screen yet — cancelling a
  booking currently has to be done directly in the database.

## One improvement for next iteration

Add a vehicles table (make, capacity, fuel type) so the usage dashboard can
report **cost per department**, not just distance — that's the number the
transport officer actually needs to justify budget requests.
