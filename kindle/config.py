"""Kindle Calendar Configuration"""

# Server settings
SERVER_URL = "http://192.168.1.100:8080"  # Change to your server IP
SYNC_INTERVAL = 30  # minutes

# Display settings
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
REFRESH_RATE = 30  # seconds

# Priority colors (grayscale values 0-255)
PRIORITY_COLORS = {
    "urgent": 0,      # Black
    "important": 128, # Gray
    "normal": 200     # Light gray
}

# Priority labels
PRIORITY_LABELS = {
    "urgent": "🔴 紧急",
    "important": "🟡 重要",
    "normal": "⚪ 一般"
}

# Date format
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# Local storage
LOCAL_DB_PATH = "/mnt/us/calendar/local_events.json"
CONFIG_PATH = "/mnt/us/calendar/config.json"

# WiFi settings
WIFI_TIMEOUT = 10  # seconds