#!/bin/sh
set -e

python3 -c "
import sqlite3, os
from app import init_db, DB_PATH
init_db()
db = sqlite3.connect(DB_PATH)
count = db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
db.close()
if count == 0:
    import seed_data
    seed_data.seed()
"

exec gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
