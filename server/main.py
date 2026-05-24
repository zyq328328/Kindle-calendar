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

def build_tree(events):
    """Build a tree structure from flat event list based on parent_id"""
    lookup = {e['id']: {**e, 'children': []} for e in events}
    roots = []
    for e in events:
        parent_id = e.get('parent_id')
        if parent_id and parent_id in lookup:
            lookup[parent_id]['children'].append(lookup[e['id']])
        else:
            roots.append(lookup[e['id']])
    return roots

@app.get("/api/events", response_model=list[Event])
def list_events():
    events = get_all_events()
    for e in events:
        e["is_countdown"] = bool(e.get("is_countdown", False))
        e["completed"] = bool(e.get("completed", False))
    return events

@app.get("/api/events/tree")
def events_tree():
    """Return events in tree structure"""
    events = get_all_events()
    for e in events:
        e["is_countdown"] = bool(e.get("is_countdown", False))
        e["completed"] = bool(e.get("completed", False))
    return build_tree(events)

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

@app.post("/api/habits/{event_id}/checkin")
def checkin_habit(event_id: int, date: str = None):
    """Mark a habit as completed for a specific date"""
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.get("type") != "habit":
        raise HTTPException(status_code=400, detail="Not a habit")
    
    today = date or datetime.now().strftime("%Y-%m-%d")
    update_event(event_id, {"last_completed_date": today, "completed": True})
    return {"status": "checked_in", "event_id": event_id, "date": today}

@app.get("/api/sync", response_model=SyncResponse)
def sync(since: Optional[str] = None):
    if since:
        events = get_events_since(since)
    else:
        events = get_all_events()

    for e in events:
        e["is_countdown"] = bool(e.get("is_countdown", False))
        e["completed"] = bool(e.get("completed", False))

    return SyncResponse(
        events=events,
        server_time=get_server_time()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)