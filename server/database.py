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
            INSERT INTO events (title, description, date, time, importance, urgency, is_countdown, countdown_target, completed, type, recurrence_rule, start_date, end_date, last_completed_date, parent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            event_data.get("end_date"),
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
    for key in ["title", "description", "date", "time", "importance", "urgency", "is_countdown", "countdown_target", "completed", "type", "recurrence_rule", "start_date", "end_date", "last_completed_date", "parent_id"]:
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
    # 按 id 去重（expand_recurrence 产生了多条同 id 记录），保留第一条（start_date 最近的原始日期）
    unique_events = {}
    for ev in all_events:
        if ev["id"] not in unique_events:
            unique_events[ev["id"]] = ev
    all_events = list(unique_events.values())
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
            ("end_date", "TEXT"),
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
    """将带重复规则的事件展开为指定日期范围内的一系列记录"""
    rule = habit.get("recurrence_rule", "none")
    if rule == "none":
        return [habit]

    import calendar
    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    habit_start = datetime.strptime(habit.get("start_date", habit["date"]), "%Y-%m-%d")
    current = max(habit_start, start)

    # 重复结束日期（没有则无期限）
    habit_end_str = habit.get("end_date") or None
    habit_end = datetime.strptime(habit_end_str, "%Y-%m-%d") if habit_end_str else None

    def _next(cur, rule):
        """返回下一个日期（不修改 cur）"""
        if rule == "daily":
            return cur + timedelta(days=1)
        elif rule == "weekdays":
            nxt = cur + timedelta(days=1)
            while nxt.weekday() >= 5:
                nxt += timedelta(days=1)
            return nxt
        elif rule == "weekly":
            return cur + timedelta(weeks=1)
        elif rule == "monthly":
            month = cur.month + 1
            year = cur.year
            if month > 12:
                month = 1
                year += 1
            max_day = calendar.monthrange(year, month)[1]
            day = min(cur.day, max_day)
            return datetime(year, month, day)
        return cur + timedelta(days=1)

    # 第一遍：收集所有日期
    all_dates = []
    cur = current
    for _ in range(1000):
        if cur > end:
            break
        if habit_end and cur > habit_end:
            break
        all_dates.append(cur.strftime("%Y-%m-%d"))
        cur = _next(cur, rule)

    # 第二遍：生成 occurrence，每个带完整的 display_dates
    occurrences = []
    cur = current
    for _ in range(1000):
        if cur > end:
            break
        if habit_end and cur > habit_end:
            break
        occ = dict(habit)
        occ["date"] = cur.strftime("%Y-%m-%d")
        occ["display_dates"] = all_dates
        last_done = habit.get("last_completed_date")
        hs = habit.get("start_date", "")
        he = habit.get("end_date", "")
        # 阶段任务语义：last_done 在区间内，则整个区间所有日期都显示完成
        if last_done and hs and he:
            occ["completed"] = bool(habit.get("completed")) and (hs <= last_done <= he)
        else:
            occ["completed"] = bool(habit.get("completed")) and last_done and last_done == cur.strftime("%Y-%m-%d")
        occ["is_countdown"] = bool(occ.get("is_countdown"))
        occurrences.append(occ)
        cur = _next(cur, rule)

    return occurrences


def get_events_in_range(start_date: str, end_date: str) -> list[dict]:
    """返回日期范围内所有事件，含展开后的重复记录"""
    all_events = get_all_events()
    result = []

    for ev in all_events:
        if ev.get("recurrence_rule", "none") != "none":
            result.extend(expand_recurrence(ev, start_date, end_date))
        else:
            ev_date = ev.get("date", "")
            ev_start = ev.get("start_date") or ev_date
            ev_end = ev.get("end_date") or ev_start
            
            # 区间重叠判断：查询范围 [start_date, end_date] 与事件区间 [ev_start, ev_end] 有无交集
            if max(start_date, ev_start) <= min(end_date, ev_end):
                # 如果事件有 start_date 和 end_date，展开到每个日期
                if ev_start != ev_end:
                    # 生成所有应该显示的日期
                    start_dt = datetime.strptime(ev_start, "%Y-%m-%d")
                    end_dt = datetime.strptime(ev_end, "%Y-%m-%d")
                    current_dt = start_dt
                    all_dates = []
                    while current_dt <= end_dt:
                        all_dates.append(current_dt.strftime("%Y-%m-%d"))
                        current_dt += datetime.timedelta(days=1)
                    
                    # 为每个日期创建一个实例，带有完整的 display_dates
                    query_start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query_end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    current_dt = max(start_dt, query_start_dt)
                    while current_dt <= min(end_dt, query_end_dt):
                        date_str = current_dt.strftime("%Y-%m-%d")
                        ev_copy = ev.copy()
                        ev_copy["date"] = date_str
                        ev_copy["display_dates"] = all_dates
                        result.append(ev_copy)
                        current_dt += datetime.timedelta(days=1)
                else:
                    # 单日事件，直接添加
                    result.append(ev)

    return result


init_db()
migrate_add_missing_columns()
migrate_priority_to_importance_urgency()
