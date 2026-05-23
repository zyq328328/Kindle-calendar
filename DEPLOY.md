# Kindle 智能台历 部署指南

## 概述

Kindle 智能台历分为两部分：
- **服务端**：运行在服务器（VM2）上，负责存储日历数据
- **Kindle端**：运行在 Kindle 设备上，负责显示和交互

两者通过局域网 WiFi 同步数据。

---

## 第一部分：服务端部署（在 VM2 服务器上执行）

### 1. 创建项目目录

```bash
mkdir -p /opt/kindle-calendar
cd /opt/kindle-calendar
```

### 2. 创建 server 目录并编写代码

在 `/opt/kindle-calendar/server/` 下创建以下文件：

**requirements.txt**
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
```

**models.py**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class EventBase(BaseModel):
    title: str
    description: Optional[str] = ""
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    priority: Literal["urgent", "important", "normal"] = "normal"
    is_countdown: bool = False
    countdown_target: Optional[str] = None
    completed: bool = False
    updated_at: Optional[str] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    priority: Optional[Literal["urgent", "important", "normal"]] = None
    is_countdown: Optional[bool] = None
    countdown_target: Optional[str] = None
    completed: Optional[bool] = None

class Event(EventBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    events: list[Event]
    server_time: str
```

**database.py**
```python
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DATABASE_PATH = "/opt/kindle-calendar/kindle_calendar.db"

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
                priority TEXT DEFAULT 'normal',
                is_countdown INTEGER DEFAULT 0,
                countdown_target TEXT,
                completed INTEGER DEFAULT 0,
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
            INSERT INTO events (title, description, date, time, priority, is_countdown, countdown_target, completed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data["title"],
            event_data.get("description", ""),
            event_data["date"],
            event_data.get("time"),
            event_data.get("priority", "normal"),
            int(event_data.get("is_countdown", False)),
            event_data.get("countdown_target"),
            int(event_data.get("completed", False)),
            now,
            now
        ))
        conn.commit()
        return get_event_by_id(c.lastrowid)

def update_event(event_id: int, event_data: dict) -> Optional[dict]:
    now = datetime.now().isoformat()
    updates = []
    values = []
    for key in ["title", "description", "date", "time", "priority", "is_countdown", "countdown_target", "completed"]:
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

init_db()
```

**main.py**
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime

from models import EventCreate, EventUpdate, Event, SyncResponse
from database import (
    get_all_events, get_events_since, get_event_by_id,
    create_event, update_event, delete_event, get_server_time
)

app = FastAPI(title="Kindle Calendar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "Kindle Calendar API"}

@app.get("/api/health")
def health():
    return {"status": "healthy", "server_time": get_server_time()}

@app.get("/api/events", response_model=list[Event])
def list_events():
    events = get_all_events()
    for e in events:
        e["is_countdown"] = bool(e["is_countdown"])
        e["completed"] = bool(e["completed"])
    return events

@app.post("/api/events", response_model=Event, status_code=201)
def create(event: EventCreate):
    event_data = event.model_dump()
    created = create_event(event_data)
    if created:
        created["is_countdown"] = bool(created["is_countdown"])
        created["completed"] = bool(created["completed"])
        return created
    raise HTTPException(status_code=500, detail="Failed to create event")

@app.get("/api/events/{event_id}", response_model=Event)
def get_event(event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event["is_countdown"] = bool(event["is_countdown"])
    event["completed"] = bool(event["completed"])
    return event

@app.put("/api/events/{event_id}", response_model=Event)
def modify_event(event_id: int, event: EventUpdate):
    existing = get_event_by_id(event_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    update_data = event.model_dump(exclude_unset=True)
    updated = update_event(event_id, update_data)
    if updated:
        updated["is_countdown"] = bool(updated["is_countdown"])
        updated["completed"] = bool(updated["completed"])
        return updated
    raise HTTPException(status_code=500, detail="Failed to update event")

@app.delete("/api/events/{event_id}")
def remove_event(event_id: int):
    if not delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted", "id": event_id}

@app.get("/api/sync", response_model=SyncResponse)
def sync(since: Optional[str] = None):
    if since:
        events = get_events_since(since)
    else:
        events = get_all_events()
    for e in events:
        e["is_countdown"] = bool(e["is_countdown"])
        e["completed"] = bool(e["completed"])
    return SyncResponse(events=events, server_time=get_server_time())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 3. 安装依赖并启动

```bash
cd /opt/kindle-calendar
pip install -r requirements.txt
python main.py
```

### 4. 设置开机自启（systemd）

创建 `/etc/systemd/system/kindle-calendar.service`：

```ini
[Unit]
Description=Kindle Calendar API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/kindle-calendar
ExecStart=/usr/bin/python3 /opt/kindle-calendar/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
systemctl daemon-reload
systemctl enable kindle-calendar
systemctl start kindle-calendar
```

### 5. 确认服务运行

```bash
curl http://localhost:8080/api/health
```

应返回：
```json
{"status":"healthy","server_time":"2026-05-20T..."}
```

### 6. 获取 VM2 的局域网 IP

```bash
hostname -I
# 或
ip addr show
```

记录返回的 IP 地址（如 `192.168.10.x`），这是 **服务端 IP**。

---

## 第二部分：Kindle 端配置

### 1. 获取服务端 IP

上一步获取的 VM2 局域网 IP，例如 `192.168.10.100`

### 2. 修改 Kindle 上的配置

通过 SSH 连接 Kindle，编辑配置：

```bash
ssh root@192.168.10.72
```

编辑 `/mnt/us/calendar/config.py`：

```python
# 把 SERVER_URL 改成 VM2 的 IP
SERVER_URL = "http://192.168.10.100:8080"
```

**注意**：需要把 `192.168.10.100` 换成你从第6步获取的实际 IP。

### 3. 启动应用

```bash
cd /mnt/us/calendar
python3 main.py
```

---

## 第三部分：测试

### 服务端测试（在任意能访问 VM2 的机器上）

```bash
# 创建测试事件
curl -X POST http://192.168.10.100:8080/api/events \
  -H "Content-Type: application/json" \
  -d '{"title":"测试事件","date":"2026-05-20","time":"10:00","priority":"important"}'

# 获取所有事件
curl http://192.168.10.100:8080/api/events
```

### Kindle 端测试

1. 运行 `python3 main.py` 后，Kindle 屏幕应显示日历界面
2. 查看是否能同步服务端数据

---

## 服务端 API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/events` | 获取所有事件 |
| POST | `/api/events` | 创建事件 |
| PUT | `/api/events/{id}` | 更新事件 |
| DELETE | `/api/events/{id}` | 删除事件 |
| GET | `/api/sync?since={timestamp}` | 增量同步 |

---

## 注意事项

1. **防火墙**：确保 VM2 的 8080 端口开放
2. **网络**：Kindle 和 VM2 必须在同一局域网
3. **日志**：查看服务端日志确认同步状态
4. **数据库**：数据存储在 `/opt/kindle-calendar/kindle_calendar.db`

---

如有问题，检查：
1. `systemctl status kindle-calendar` 服务状态
2. `curl http://localhost:8080/api/health` 本地连通性
3. Kindle 能 ping 通 VM2 吗？