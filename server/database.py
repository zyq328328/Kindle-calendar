import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DATABASE_PATH = "/opt/kindle-calendar/kindle_calendar.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
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
                importance TEXT DEFAULT 'not_important',
                urgency TEXT DEFAULT 'not_urgent',
                is_countdown INTEGER DEFAULT 0,
                countdown_target TEXT,
                completed INTEGER DEFAULT 0,
                type TEXT DEFAULT 'schedule',
                recurrence_rule TEXT DEFAULT 'none',
                start_date TEXT,
                last_completed_date TEXT,
                parent_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
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
            INSERT INTO events (title, description, date, time, importance, urgency, is_countdown, countdown_target, completed, type, recurrence_rule, start_date, last_completed_date, parent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data["title"],
            event_data.get("description", ""),
            event_data["date"],
            event_data.get("time"),
            event_data.get("importance", "not_important"),
            event_data.get("urgency", "not_urgent"),
            int(event_data.get("is_countdown", False)),
            event_data.get("countdown_target"),
            int(event_data.get("completed", False)),
            event_data.get("type", "schedule"),
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
    for key in ["title", "description", "date", "time", "importance", "urgency", "is_countdown", "countdown_target", "completed", "type", "recurrence_rule", "start_date", "last_completed_date", "parent_id"]:
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

def get_children(parent_id: int) -> list[dict]:
    """获取某个父任务的所有直接子任务"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM events WHERE parent_id = ? ORDER BY date ASC, time ASC", (parent_id,))
        rows = c.fetchall()
        return [dict(row) for row in rows]

def get_event_tree() -> list[dict]:
    """获取扁平化的事件列表，每个事件带 children 字段（含子任务），重复事件自动展开"""
    import datetime
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=90)).isoformat()
    end = (today + datetime.timedelta(days=270)).isoformat()
    # 用 get_events_in_range 展开重复规则
    all_events = get_events_in_range(start, end)
    # 构建 parent_id -> children 映射
    children_map = {}
    for ev in all_events:
        pid = ev.get("parent_id")
        if pid is not None:
            if pid not in children_map:
                children_map[pid] = []
            children_map[pid].append(ev)
    # 给每个事件附加 children
    for ev in all_events:
        ev["children"] = children_map.get(ev["id"], [])
    # 返回顶级任务（无 parent_id）
    return [ev for ev in all_events if ev.get("parent_id") is None]

def migrate_add_missing_columns():
    """为已有表添加新字段"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(events)")
        existing = {col[1] for col in c.fetchall()}
        migrations = [
            ("importance", "TEXT DEFAULT 'not_important'"),
            ("urgency", "TEXT DEFAULT 'not_urgent'"),
            ("type", "TEXT DEFAULT 'schedule'"),
            ("recurrence_rule", "TEXT DEFAULT 'none'"),
            ("start_date", "TEXT"),
            ("last_completed_date", "TEXT"),
            ("parent_id", "INTEGER REFERENCES events(id) ON DELETE CASCADE"),
        ]
        for col_name, col_def in migrations:
            if col_name not in existing:
                c.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_def}")
        conn.commit()


def migrate_priority_to_importance_urgency():
    """一次性迁移：priority -> importance + urgency"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(events)")
        columns = {col[1] for col in c.fetchall()}
        if "importance" not in columns:
            return  # 还没添加新字段，跳过

        if "priority" not in columns:
            return  # priority 列不存在，无需迁移

        c.execute("SELECT id, priority FROM events WHERE priority IS NOT NULL AND priority != '' AND priority != 'normal'")
        for row in c.fetchall():
            event_id = row[0]
            priority = row[1]
            if priority == "urgent":
                imp, urg = "important", "urgent"
            elif priority == "important":
                imp, urg = "important", "not_urgent"
            else:
                imp, urg = "not_important", "not_urgent"
            c.execute("UPDATE events SET importance=?, urgency=? WHERE id=?", (imp, urg, event_id))
        conn.commit()

def get_server_time() -> str:
    return datetime.now().isoformat()


def expand_recurrence(habit: dict, start_date: str, end_date: str) -> list[dict]:
    """将带重复规则的 habit 展开为指定日期范围内的一系列打卡记录"""
    rule = habit.get("recurrence_rule", "none")
    if rule == "none":
        return [habit]

    import calendar
    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # 从 habit 开始日期（或查询范围起始）到末尾，生成应打卡的日期
    habit_start = datetime.strptime(habit.get("start_date", habit["date"]), "%Y-%m-%d")
    # 直接从查询范围起始日和 habit 起始日的较大者开始，避免远期习惯迭代过慢
    current = max(habit_start, start)

    occurrences = []
    while current <= end:
        occ = dict(habit)
        occ["date"] = current.strftime("%Y-%m-%d")
        last_done = habit.get("last_completed_date")
        occ["completed"] = bool(last_done and last_done == current.strftime("%Y-%m-%d"))
        # SQLite stores booleans as integers, ensure proper bool conversion
        occ["is_countdown"] = bool(occ.get("is_countdown"))
        occ["completed"] = bool(occ.get("completed"))
        occurrences.append(occ)
        # 推进到下一个周期
        if rule == "daily":
            current += timedelta(days=1)
        elif rule == "weekdays":
            current += timedelta(days=1)
            while current.weekday() >= 5:
                current += timedelta(days=1)
        elif rule == "weekly":
            current += timedelta(weeks=1)
        elif rule == "monthly":
            # 使用 calendar 模块正确计算下个月的日期
            month = current.month
            year = current.year
            month += 1
            if month > 12:
                month = 1
                year += 1
            # 获取目标月份的最大天数，避免硬编码列表
            max_day = calendar.monthrange(year, month)[1]
            day = min(current.day, max_day)
            current = datetime(year, month, day)

    return occurrences


def get_events_in_range(start_date: str, end_date: str) -> list[dict]:
    """返回日期范围内所有事件，含展开后的习惯打卡记录"""
    all_events = get_all_events()
    result = []

    for ev in all_events:
        if ev.get("recurrence_rule", "none") != "none":
            result.extend(expand_recurrence(ev, start_date, end_date))
        else:
            # 过滤不在范围内的普通事件
            ev_date = ev.get("date", "")
            if start_date <= ev_date <= end_date:
                result.append(ev)

    return result


init_db()
migrate_add_missing_columns()
migrate_priority_to_importance_urgency()
