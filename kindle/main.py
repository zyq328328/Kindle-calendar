"""Kindle Calendar - Main Application Entry Point

A smart calendar application for Kindle Touch with WiFi sync and
e-ink display optimized UI.
"""

import os
import sys
import time
import threading
import struct
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from eink import get_display
from models import EventStore, Event
from sync import SyncManager

class KindleCalendar:
    """Main application class"""

    def __init__(self):
        self.display = get_display()

        os.makedirs(os.path.dirname(config.LOCAL_DB_PATH), exist_ok=True)
        self.event_store = EventStore(config.LOCAL_DB_PATH)

        self.sync_manager = SyncManager(self.event_store)

        from ui import UIManager
        self.ui_manager = UIManager(self.display, self.event_store, self.sync_manager)

        self.running = True
        self.last_touch_x = None
        self.last_touch_y = None

        # Open input device once, keep it open
        self._input_file = None
        self._open_input_device()

    def _open_input_device(self):
        """Open the touchscreen input device"""
        for dev in ["/dev/input/event1", "/dev/input/event0"]:
            if os.path.exists(dev):
                try:
                    self._input_file = open(dev, "rb")
                    print(f"Opened input device: {dev}")
                    return
                except:
                    pass
        print("Warning: No input device available")

    def _read_input(self) -> str:
        """Read user input from input device

        Returns: 'swipe_left', 'swipe_right', 'tap_x_y', or None
        """
        if not self._input_file:
            return None

        try:
            import select
            if select.select([self._input_file], [], [], 0.05)[0]:
                data = self._input_file.read(16)  # kernel input_event is 16 bytes
                if len(data) < 16:
                    return None

                ts_sec, ts_usec, t_type, code, value = struct.unpack("IIHHI", data)

                # EV_ABS = 3, ABS_MT_POSITION_X = 53, ABS_MT_POSITION_Y = 54
                # EV_KEY = 1, BTN_TOUCH = 330 (0x14a)
                if t_type == 3:  # EV_ABS
                    if code == 53:  # ABS_MT_POSITION_X
                        self.last_touch_x = value
                    elif code == 54:  # ABS_MT_POSITION_Y
                        self.last_touch_y = value
                elif t_type == 1 and code == 330:  # BTN_TOUCH
                    if value == 1:  # Touch down
                        self._touch_start_x = self.last_touch_x
                    elif value == 0 and self.last_touch_x is not None and self.last_touch_y is not None:
                        # Touch up - check for swipe
                        start_x = getattr(self, '_touch_start_x', self.last_touch_x)
                        dx = self.last_touch_x - (start_x or 0)
                        if abs(dx) > 50:
                            direction = "swipe_right" if dx > 0 else "swipe_left"
                            self.last_touch_x = None
                            self.last_touch_y = None
                            return direction
                        else:
                            result = f"tap_{self.last_touch_x}_{self.last_touch_y}"
                            self.last_touch_x = None
                            self.last_touch_y = None
                            return result

        except Exception as e:
            print(f"Input error: {e}")

        return None

        return None

    def run(self):
        """Main application loop"""
        print("Kindle Calendar starting...")

        # Initial render immediately
        self.ui_manager.render()
        print("Initial render done")

        # Try sync in background
        import threading
        def background_sync():
            print("Background sync...")
            try:
                self.sync_manager.sync()
                print("Sync done")
                self.ui_manager.render()  # Re-render after sync
            except Exception as e:
                print(f"Sync error: {e}")

        sync_thread = threading.Thread(target=background_sync, daemon=True)
        sync_thread.start()

        # Main loop
        while self.running:
            try:
                action = self._read_input()

                if action:
                    print(f"Action: {action}")
                    self.ui_manager.handle_input(action)
                    self.ui_manager.render()

                time.sleep(0.1)

            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

        self.display.close()

def create_sample_events(event_store: EventStore):
    """Create sample events for testing"""
    today = datetime.now()

    sample_events = [
        Event(title="团队周会", date=today.strftime("%Y-%m-%d"), time="10:00", priority="important"),
        Event(title="项目截止", date=today.strftime("%Y-%m-%d"), time="17:00", priority="urgent"),
        Event(title="健身计划", date=today.strftime("%Y-%m-%d"), time="18:30", priority="normal"),
        Event(title="生日派对", date=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
              priority="important", is_countdown=True, countdown_target=(today + timedelta(days=7)).strftime("%Y-%m-%d")),
    ]

    for event in sample_events:
        event_store.add(event)

if __name__ == "__main__":
    from datetime import timedelta

    app = KindleCalendar()

    if not app.event_store.events:
        print("Creating sample events...")
        create_sample_events(app.event_store)

    app.run()