from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class EventBase(BaseModel):
    title: str
    description: Optional[str] = ""
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    importance: Literal["important", "not_important"] = "not_important"
    urgency: Literal["urgent", "not_urgent"] = "not_urgent"
    is_countdown: bool = False
    countdown_target: Optional[str] = None
    completed: bool = False
    type: Literal["schedule", "todo", "habit"] = "schedule"  # 日程 or 待办 or 习惯
    recurrence_rule: Literal["none", "daily", "weekdays", "weekly", "monthly"] = "none"  # 重复周期
    start_date: Optional[str] = None  # YYYY-MM-DD 习惯开始日期
    last_completed_date: Optional[str] = None  # YYYY-MM-DD 上次打卡日期
    updated_at: Optional[str] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    importance: Optional[Literal["important", "not_important"]] = None
    urgency: Optional[Literal["urgent", "not_urgent"]] = None
    is_countdown: Optional[bool] = None
    countdown_target: Optional[str] = None
    completed: Optional[bool] = None
    type: Optional[Literal["schedule", "todo", "habit"]] = None
    recurrence_rule: Optional[Literal["none", "daily", "weekdays", "weekly", "monthly"]] = None
    start_date: Optional[str] = None
    last_completed_date: Optional[str] = None

class Event(EventBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    events: list[Event]
    server_time: str
