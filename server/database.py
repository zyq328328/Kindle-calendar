import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DATABASE_PATH = "kindle_calendar.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                date TEXT NOT NULL,
                time TEXT,
                type TEXT DEFAULT 'schedule',
                importance TEXT DEFAULT 'not_important',
                urgency TEXT DEFAULT 'not_urgent',
                is_countdown INTEGER DEFAULT 0,
                countdown_target TEXT,
                completed INTEGER DEFAULT 0,
                recurrence_rule TEXT DEFAULT 'none',
                start_date TEXT,
                last_completed_date TEXT,
                parent_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Add missing columns if they don't exist (for database migration)
        try:
            c.execute("ALTER TABLE events ADD COLUMN importance TEXT DEFAULT 'not_important'")
        except:
            pass
        try:
            c.execute("ALTER TABLE events ADD COLUMN urgency TEXT DEFAULT 'not_urgent'")
        except:
            pass
        try:
            c.execute("ALTER TABLE events ADD COLUMN type TEXT DEFAULT 'schedule'")
        except:
            pass
        try:
            c.execute("ALTER TABLE events ADD COLUMN recurrence_rule TEXT DEFAULT 'none'")
        except:
            pass
        try:
            c.execute("ALTER TABLE events ADD COLUMN start_date TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE events ADD COLUMN last_completed_date TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE events ADD COLUMN parent_id INTEGER")
        except:
            pass
        conn.commit()

def get_all_events() -> list[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM events ORDER BY date ASC, time ASC")
        rows = c.fetchall()
        return [dict(row) for row in rows]

def get_events_since(timestamp: str) -> list[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM events WHERE updated_at > ? ORDER BY date ASC, time ASC", (timestamp,))
        rows = c.fetchall()
        return [dict(row) for row in rows]

def get_event_by_id(event_id: int) -> Optional[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = c.fetchone()
        return dict(row) if row else None

def create_event(event_data: dict) -> dict:
    now = datetime.now().isoformat()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO events (title, description, date, time, type, importance, urgency, is_countdown, countdown_target, completed, recurrence_rule, start_date, last_completed_date, parent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data["title"],
            event_data.get("description", ""),
            event_data["date"],
            event_data.get("time"),
            event_data.get("type", "schedule"),
            event_data.get("importance", "not_important"),
            event_data.get("urgency", "not_urgent"),
            int(event_data.get("is_countdown", False)),
            event_data.get("countdown_target"),
            int(event_data.get("completed", False)),
            event_data.get("recurrence_rule", "none"),
            event_data.get("start_date"),
            event_data.get("last_completed_date"),
            event_data.get("parent_id"),
            now,
            now
        ))
        conn.commit()
        return get_event_by_id(c.lastrowid)

def update_event(event_id: int, event_data: dict) -> Optional[dict]:
    now = datetime.now().isoformat()
    updates = []
    values = []

    for key in ["title", "description", "date", "time", "type", "importance", "urgency", "is_countdown", "countdown_target", "completed", "recurrence_rule", "start_date", "last_completed_date", "parent_id"]:
        if key in event_data:
            updates.append(f"{key} = ?")
            if key in ["is_countdown", "completed"]:
                values.append(int(event_data[key]))
            else:
                values.append(event_data[key])

    if not updates:
        return get_event_by_id(event_id)

    updates.append("updated_at = ?")
    values.append(now)
    values.append(event_id)

    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
        return get_event_by_id(event_id)

def delete_event(event_id: int) -> bool:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return c.rowcount > 0

def get_server_time() -> str:
    return datetime.now().isoformat()

# Initialize database on import
init_db()