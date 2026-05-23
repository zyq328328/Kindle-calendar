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
    countdown_target: Optional[str] = None  # YYYY-MM-DD for countdown events
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