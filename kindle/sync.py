"""WiFi Sync Module for Kindle Calendar"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime
from typing import Optional
from models import Event, EventStore
import config

class SyncManager:
    """Handle synchronization with remote server"""

    def __init__(self, event_store: EventStore, server_url: str = None):
        self.event_store = event_store
        self.server_url = server_url or config.SERVER_URL
        self.last_sync: Optional[str] = None
        self.wifi_available = False

    def check_wifi(self) -> bool:
        """Check if WiFi is connected"""
        try:
            # Try to reach the server
            urllib.request.urlopen(
                f"{self.server_url}/api/health",
                timeout=config.WIFI_TIMEOUT
            )
            self.wifi_available = True
            return True
        except (urllib.error.URLError, ConnectionError):
            self.wifi_available = False
            return False

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        """Make HTTP request to server"""
        url = f"{self.server_url}{endpoint}"
        try:
            if method == "GET":
                req = urllib.request.Request(url)
            else:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method=method
                )

            with urllib.request.urlopen(req, timeout=config.WIFI_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"Sync error: {e}")
            return None

    def sync(self) -> bool:
        """Perform full sync with server"""
        if not self.check_wifi():
            print("WiFi not available, skipping sync")
            return False

        # Get server events
        params = f"?since={self.last_sync}" if self.last_sync else ""
        response = self._make_request("GET", f"/api/sync{params}")

        if not response:
            return False

        # Convert to Event objects
        remote_events = [Event.from_dict(e) for e in response.get("events", [])]

        # Merge with local
        self.event_store.merge_remote(remote_events)

        # Update last sync time
        self.last_sync = response.get("server_time")

        return True

    def push_event(self, event: Event) -> bool:
        """Push single event to server"""
        if not self.check_wifi():
            return False

        if event.id == 0:
            # New event
            response = self._make_request("POST", "/api/events", event.to_dict())
        else:
            # Update existing
            response = self._make_request("PUT", f"/api/events/{event.id}", event.to_dict())

        if response:
            # Update local event with server response
            server_event = Event.from_dict(response)
            local_event = next((e for e in self.event_store.events if e.id == event.id), None)
            if local_event:
                for key, value in server_event.to_dict().items():
                    setattr(local_event, key, value)
            return True
        return False

    def delete_event(self, event_id: int) -> bool:
        """Delete event from server"""
        if not self.check_wifi():
            return False

        response = self._make_request("DELETE", f"/api/events/{event_id}")
        return response is not None

def start_background_sync(event_store: EventStore):
    """Start background sync daemon (runs in separate thread)"""
    import threading

    sync_manager = SyncManager(event_store)

    def sync_loop():
        while True:
            sync_manager.sync()
            time.sleep(config.SYNC_INTERVAL * 60)

    thread = threading.Thread(target=sync_loop, daemon=True)
    thread.start()
    return sync_manager