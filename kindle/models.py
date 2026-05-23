"""Calendar Event Data Models"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional, Literal
import json

@dataclass
class Event:
    """Calendar event model"""
    id: int = 0
    title: str = ""
    description: str = ""
    date: str = ""  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    priority: Literal["urgent", "important", "normal"] = "normal"
    is_countdown: bool = False
    countdown_target: Optional[str] = None
    completed: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        # Handle sqlite boolean conversion
        if "is_countdown" in data and isinstance(data["is_countdown"], int):
            data["is_countdown"] = bool(data["is_countdown"])
        if "completed" in data and isinstance(data["completed"], int):
            data["completed"] = bool(data["completed"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def days_until(self) -> Optional[int]:
        """Calculate days until countdown target"""
        if self.is_countdown and self.countdown_target:
            target = datetime.strptime(self.countdown_target, "%Y-%m-%d")
            delta = target - datetime.now()
            return delta.days
        return None

    @property
    def is_today(self) -> bool:
        """Check if event is today"""
        return self.date == date.today().strftime("%Y-%m-%d")

    @property
    def is_past(self) -> bool:
        """Check if event date has passed"""
        if self.date:
            event_date = datetime.strptime(self.date, "%Y-%m-%d")
            return event_date < datetime.now()
        return False

class EventStore:
    """Local event storage"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.events: list[Event] = []
        self._load()

    def _load(self):
        """Load events from local storage"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.events = [Event.from_dict(e) for e in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self.events = []

    def save(self):
        """Save events to local storage"""
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.events], f, ensure_ascii=False, indent=2)

    def add(self, event: Event):
        """Add new event"""
        self.events.append(event)
        self.save()

    def update(self, event_id: int, updates: dict) -> Optional[Event]:
        """Update existing event"""
        for e in self.events:
            if e.id == event_id:
                for key, value in updates.items():
                    if hasattr(e, key):
                        setattr(e, key, value)
                self.save()
                return e
        return None

    def delete(self, event_id: int) -> bool:
        """Delete event by ID"""
        before = len(self.events)
        self.events = [e for e in self.events if e.id != event_id]
        if len(self.events) < before:
            self.save()
            return True
        return False

    def get_by_date(self, target_date: str) -> list[Event]:
        """Get events for specific date"""
        return [e for e in self.events if e.date == target_date]

    def get_countdowns(self) -> list[Event]:
        """Get all countdown events"""
        return [e for e in self.events if e.is_countdown]

    def get_pending(self) -> list[Event]:
        """Get incomplete non-countdown events"""
        return [e for e in self.events if not e.completed and not e.is_countdown]

    def merge_remote(self, remote_events: list[Event]):
        """Merge remote events, preferring newer by updated_at"""
        remote_dict = {e.id: e for e in remote_events}
        local_dict = {e.id: e for e in self.events}

        for event_id, remote_event in remote_dict.items():
            if event_id in local_dict:
                # Compare updated_at, keep newer
                if remote_event.updated_at > local_dict[event_id].updated_at:
                    local_dict[event_id] = remote_event
            else:
                local_dict[event_id] = remote_event

        self.events = list(local_dict.values())
        self.save()