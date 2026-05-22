"""
方案B 服务端 - 触摸路由API
扩展现有 8082 FastAPI 服务，增加 /touch, /region/current, /frame/update 端点
"""
import base64
import os
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 复用现有kindle-calendar的Event模型（用别名避免与本地models冲突）
import sys
sys.path.insert(0, "/opt/kindle-calendar/server")
import models as km  # kindle-calendar models
import database
from regions import route_touch, get_current_view, get_current_date, set_view, set_date

# 方案B本地模型
from plan_b_models import TouchRequest, TouchResponse, RegionCurrent, FrameUpdate

app = FastAPI(title="Kindle Calendar API - Plan B", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 现有端点（保持兼容）============

@app.get("/")
def root():
    return {"status": "ok", "service": "Kindle Calendar API - Plan B"}

@app.get("/api/health")
def health():
    return {"status": "healthy", "server_time": database.get_server_time()}

@app.get("/api/events", response_model=list[km.Event])
def list_events():
    events = database.get_all_events()
    for e in events:
        e["is_countdown"] = bool(e["is_countdown"])
        e["completed"] = bool(e["completed"])
    return events

@app.post("/api/events", response_model=km.Event, status_code=201)
def create(event: km.EventCreate):
    event_data = event.model_dump()
    created = database.create_event(event_data)
    if created:
        created["is_countdown"] = bool(created["is_countdown"])
        created["completed"] = bool(created["completed"])
        return created
    raise HTTPException(status_code=500, detail="Failed to create event")

@app.get("/api/events/{event_id}", response_model=km.Event)
def get_event(event_id: int):
    event = database.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event["is_countdown"] = bool(event["is_countdown"])
    event["completed"] = bool(event["completed"])
    return event

@app.put("/api/events/{event_id}", response_model=km.Event)
def modify_event(event_id: int, event: km.EventUpdate):
    existing = database.get_event_by_id(event_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    update_data = event.model_dump(exclude_unset=True)
    updated = database.update_event(event_id, update_data)
    if updated:
        updated["is_countdown"] = bool(updated["is_countdown"])
        updated["completed"] = bool(updated["completed"])
        return updated
    raise HTTPException(status_code=500, detail="Failed to update event")

@app.delete("/api/events/{event_id}")
def remove_event(event_id: int):
    if not database.delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted", "id": event_id}

@app.get("/api/sync", response_model=km.SyncResponse)
def sync(since: str | None = None):
    if since:
        events = database.get_events_since(since)
    else:
        events = database.get_all_events()
    for e in events:
        e["is_countdown"] = bool(e["is_countdown"])
        e["completed"] = bool(e["completed"])
    return km.SyncResponse(events=events, server_time=database.get_server_time())

# ============ 方案B 触摸路由端点 ==============

@app.post("/touch", response_model=TouchResponse)
def touch(req: TouchRequest):
    """
    POST /touch - 触摸路由
    请求体: {"x": int, "y": int, "action": "tap" | "release"}
    响应: {"success": true, "action": "...", "view": "..."}
    """
    action, view = route_touch(req.x, req.y, req.action)
    return TouchResponse(success=True, action=action, view=view)

@app.get("/region/current", response_model=RegionCurrent)
def region_current():
    """
    GET /region/current - 返回当前视图
    响应: {"view": "day" | "three_day" | "todo" | "habit", "date": "YYYY-MM-DD"}
    """
    return RegionCurrent(view=get_current_view(), date=get_current_date())

@app.post("/region/switch")
def region_switch(view: str):
    """
    POST /region/switch?view=day - 切换视图
    """
    valid = ["day", "three_day", "todo", "habit"]
    if view not in valid:
        raise HTTPException(status_code=400, detail=f"view must be one of {valid}")
    set_view(view)
    return {"status": "ok", "view": view}

@app.post("/region/date")
def region_date(d: str):
    """
    POST /region/date?d=2026-05-21 - 设置当前日期
    """
    try:
        parsed = date.fromisoformat(d)
        set_date(parsed)
        return {"status": "ok", "date": d}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

# ============ 方案A帧更新端点（备用）============

FRAME_DIR = Path("/opt/kindle-calendar/plan_b/frames")
FRAME_DIR.mkdir(parents=True, exist_ok=True)
_latest_frame: bytes | None = None

@app.post("/frame/update")
def frame_update(req: FrameUpdate):
    """
    POST /frame/update - 接收base64编码的帧图片并存储
    方案A验证后回退用
    """
    global _latest_frame
    try:
        img_data = base64.b64decode(req.image_base64)
        _latest_frame = img_data
        ts = date.today().isoformat()
        frame_path = FRAME_DIR / f"frame_{ts}.png"
        with open(frame_path, "wb") as f:
            f.write(img_data)
        return {"status": "ok", "saved": str(frame_path)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {e}")

@app.get("/frame/latest")
def frame_latest():
    """GET /frame/latest - 返回最新帧图片"""
    if _latest_frame:
        from fastapi.responses import Response
        return Response(content=_latest_frame, media_type="image/png")
    raise HTTPException(status_code=404, detail="No frame available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
