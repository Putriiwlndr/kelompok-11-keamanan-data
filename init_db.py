# init_db.py  (versi baru)
import pathlib
import sqlite3

DB_PATH = pathlib.Path('cv.db')
conn     = sqlite3.connect(DB_PATH)
c        = conn.cursor()

# --- Tabel user (tak berubah) ---
c.execute("""
CREATE TABLE IF NOT EXISTS user (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
""")

# --- Tabel cv (skema lengkap) ---
c.execute("""
CREATE TABLE IF NOT EXISTS cv (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    address         TEXT,
    linkedin        TEXT,
    github          TEXT,
    summary         TEXT,
    education       TEXT,
    experience      TEXT,
    projects        TEXT,
    certifications  TEXT,
    skills          TEXT,
    languages       TEXT,
    photo_url       TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
""")

conn.commit()
conn.close()
print("Database initialized ✅")
