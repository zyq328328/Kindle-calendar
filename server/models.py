from pydantic import BaseModel
from typing import Optional

class EventBase(BaseModel):
    title: str
    description: Optional[str] = ""
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    type: str = "schedule"  # schedule, todo, habit
    importance: str = "not_important"  # important, not_important
    urgency: str = "not_urgent"  # urgent, not_urgent
    is_countdown: bool = False
    countdown_target: Optional[str] = None
    completed: bool = False
    recurrence_rule: str = "none"  # none, daily, weekdays, weekly, monthly
    start_date: Optional[str] = None
    last_completed_date: Optional[str] = None
    parent_id: Optional[int] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    type: Optional[str] = None
    importance: Optional[str] = None
    urgency: Optional[str] = None
    is_countdown: Optional[bool] = None
    countdown_target: Optional[str] = None
    completed: Optional[bool] = None
    recurrence_rule: Optional[str] = None
    start_date: Optional[str] = None
    last_completed_date: Optional[str] = None
    parent_id: Optional[int] = None

class Event(EventBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class SyncResponse(BaseModel):
    events: list[Event]
    server_time: str