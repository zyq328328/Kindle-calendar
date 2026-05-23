#!/usr/bin/env python3
"""
Kindle calendar renderer - three-column layout
800x600 landscape
- Left: Date/time display (large font)
- Middle: Today's schedule list
- Right: Navigation menu
"""
import os, sys, json, datetime, urllib.request, functools, time
from PIL import Image, ImageDraw, ImageFont

SERVER_URL = os.environ.get("SERVER_URL", "http://192.168.10.7:8082/api/events")

# ========== Size Constants ==========
W, H = 800, 600

# Three-column layout
LEFT_W = 180       # Left date/time panel width
RIGHT_W = 60       # Right navigation width
MIDDLE_W = W - LEFT_W - RIGHT_W  # Middle content width

# Color definitions
LEFT_BG = 245      # Left panel background
RIGHT_BG = 180      # Right navigation background
RIGHT_FG = 220     # Right text color
RIGHT_ACTIVE = 80 # Selected item background

# Right navigation items (top to bottom)
NAV_ITEMS = [
    ("日", "day"),
    ("3日", "three_day"),
    ("待办", "list"),
    ("四象", "quadrant"),
    ("刷新", "refresh"),
    ("设置", "settings"),
]

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAYS_SHORT = ["一", "二", "三", "四", "五", "六", "日"]

def make_font(size):
    """Create font object - use Kindle's Chinese font"""
    chinese_fonts = [
        "/usr/java/lib/fonts/STHeitiMedium.ttf",
        "/usr/java/lib/fonts/STHeitiBold.ttf",
        "/usr/java/lib/fonts/STSongMedium.ttf",
        "/usr/java/lib/fonts/STSongBold.ttf",
    ]
    for font_path in chinese_fonts:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            continue
    # Fallback to English fonts
    try:
        return ImageFont.truetype("/usr/java/lib/fonts/Bookerly-Regular.ttf", size)
    except:
        return ImageFont.load_default()

def tb(font_size, text):
    """Text bounding box width - using font_size directly"""
    width = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fff':  # Chinese chars
            width += font_size
        else:  # English chars
            width += font_size * 0.6
    return width

def fetch_events(date_str=None, max_retries=3):
    """Fetch events with retry mechanism"""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(SERVER_URL)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if date_str:
                    return [e for e in data if e.get("date", "").startswith(date_str)]
                return data
        except Exception as e:
            print(f"[renderer] fetch attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)
    return []

def render_left_panel(draw):
    """Render left date/time panel"""
    draw.rectangle([(0, 0), (LEFT_W - 1, H)], fill=LEFT_BG)
    
    now = datetime.datetime.now()
    day = now.day
    month = now.month
    year = now.year
    weekday = WEEKDAYS[now.weekday()]
    time_str = now.strftime("%H:%M")
    
    font_time = make_font(32)
    font_day = make_font(96)
    font_ym = make_font(22)
    font_weekday = make_font(24)
    
    draw.text((15, 15), time_str, font=font_time, fill=0)
    draw.text((15, 60), str(day), font=font_day, fill=0)
    draw.text((15, 170), f"{year}年{month:02d}月", font=font_ym, fill=0)
    draw.text((15, 200), weekday, font=font_weekday, fill=0)

def render_right_nav(draw, active_view):
    """Render right navigation bar"""
    draw.rectangle([(W - RIGHT_W, 0), (W - 1, H)], fill=RIGHT_BG)
    
    item_h = H // len(NAV_ITEMS)
    
    for i, (label, view) in enumerate(NAV_ITEMS):
        y = i * item_h
        is_active = (view == active_view)
        
        if is_active:
            draw.rectangle([(W - RIGHT_W + 2, y + 2), (W - 2, y + item_h - 2)], fill=RIGHT_ACTIVE)
        
        font_size = 16 if len(label) == 2 else 14
        font = make_font(font_size)
        label_w = tb(font_size, label)
        label_x = W - RIGHT_W + (RIGHT_W - label_w) // 2
        label_y = y + (item_h - font_size) // 2 - 2
        draw.text((label_x, label_y), label, font=font, fill=255 if is_active else 0)

def touch_to_view(x, y):
    """Convert touch coordinates to view name"""
    if x < W - RIGHT_W:
        return None
    item_h = H // len(NAV_ITEMS)
    idx = int(y // item_h)
    if 0 <= idx < len(NAV_ITEMS):
        return NAV_ITEMS[idx][1]
    return None

def render_day_or_home_view(draw, date_str, events, content_x, is_home=False):
    """Day/Home view - separate schedules and todos"""
    font_title = make_font(24)
    font_small = make_font(18)
    font_section = make_font(20)
    
    if is_home:
        today = datetime.date.today()
        d = today
        date_str = today.isoformat()
    else:
        d = datetime.date.fromisoformat(date_str)
    
    wd = WEEKDAYS[d.weekday()]
    
    y = 20
    if is_home:
        draw.text((content_x + 20, y), "今日", font=font_title, fill=0)
    else:
        draw.text((content_x + 20, y), f"{d.month}月{d.day}日 {wd}", font=font_title, fill=0)
    y += 45
    
    day_events = [e for e in events if e.get("date") == date_str]
    schedules = [e for e in day_events if e.get("type") == "schedule"]
    todos = [e for e in day_events if e.get("type") in ("todo", "habit")]
    
    # 日程 section
    draw.text((content_x + 20, y), "【日程】", font=font_section, fill=0)
    y += 30
    
    if not schedules:
        draw.text((content_x + 30, y), "暂无日程", font=font_small, fill=150)
        y += 25
    else:
        for ev in schedules[:5]:
            time_str = ev.get("time", "")[:5]
            title = ev.get("title", "")[:14]
            if time_str:
                draw.text((content_x + 30, y), time_str, font=font_small, fill=80)
            draw.text((content_x + 85, y), title, font=font_small, fill=0)
            y += 25
    
    y += 10
    
    # 待办 section
    draw.text((content_x + 20, y), "【待办】", font=font_section, fill=0)
    y += 30
    
    if not todos:
        draw.text((content_x + 30, y), "暂无待办", font=font_small, fill=150)
    else:
        for ev in todos[:6]:
            title = ev.get("title", "")[:16]
            draw.text((content_x + 30, y), "□", font=font_small, fill=80)
            draw.text((content_x + 50, y), title, font=font_small, fill=0)
            y += 25

def render_home_view(draw, events, content_x):
    """Home view"""
    render_day_or_home_view(draw, None, events, content_x, is_home=True)

def render_day_view(draw, date_str, events, content_x):
    """Day view"""
    render_day_or_home_view(draw, date_str, events, content_x, is_home=False)

def group_events_by_date(events, center_date):
    """Group events by date from already fetched list"""
    result = {}
    for offset in [-1, 0, 1]:
        d = center_date + datetime.timedelta(days=offset)
        date_key = d.isoformat()
        result[date_key] = [e for e in events if e.get("date", "").startswith(date_key)]
    return result

def render_three_day_view(draw, date_str, events_by_date, content_x=LEFT_W, content_w=None):
    """Three-day view: 3 columns of date + schedule"""
    font_date = make_font(22)
    font_small = make_font(20)
    
    if content_w is None:
        content_w = MIDDLE_W
    
    center = datetime.date.fromisoformat(date_str)
    dates = [center + datetime.timedelta(days=offset) for offset in [-1, 0, 1]]
    
    col_w = content_w // 3
    x = content_x
    
    for i, d in enumerate(dates):
        date_key = d.isoformat()
        events = events_by_date.get(date_key, [])
        wd = WEEKDAYS_SHORT[d.weekday()]
        
        # Date header
        is_today = (d == datetime.date.today())
        bg_color = 210 if is_today else 255
        draw.rectangle([(x, 5), (x + col_w - 5, 50)], fill=bg_color)
        date_str = f"{d.month}/{d.day}"
        draw.text((x + 8, 8), date_str, font=font_date, fill=0)
        draw.text((x + 8, 30), f"周{wd}", font=font_small, fill=100)
        
        # Events
        y = 52
        for ev in events[:5]:
            time_str = ev.get("time", "")[:5]
            title = ev.get("title", "")[:12]
            if time_str:
                draw.text((x + 5, y), time_str, font=font_small, fill=80)
            draw.text((x + 55, y), title, font=font_small, fill=0)
            y += 30
        
        # Column separator
        if i < len(dates) - 1:
            line_x = x + col_w - 3
            draw.line([(line_x, 5), (line_x, H - 10)], fill=200, width=1)
        
        x += col_w

def render_todo_view(draw, events, content_x):
    """Todo list view"""
    font_title = make_font(24)
    font_small = make_font(20)
    
    y = 20
    draw.text((content_x + 20, y), "待办列表", font=font_title, fill=0)
    y += 40
    
    todos = [e for e in events if e.get("type") == "todo" or e.get("type") == "habit"]
    todos = sorted(todos, key=lambda x: (x.get("importance") == "important", x.get("urgency") == "urgent"))
    
    if not todos:
        draw.text((content_x + 20, y), "暂无待办", font=font_small, fill=100)
        return
    
    for ev in todos[:10]:
        title = ev.get("title", "")[:18]
        completed = ev.get("completed", False)
        fill_color = 150 if completed else 0
        draw.text((content_x + 20, y), title, font=font_small, fill=fill_color)
        y += 28

QUADRANT_LABELS = [
    ("重要紧急", "important", "urgent"),
    ("重要不紧急", "important", "not_urgent"),
    ("紧急不重要", "not_important", "urgent"),
    ("不紧急不重要", "not_important", "not_urgent"),
]

def render_quadrant_view(draw, events, content_x):
    """Four quadrant view - only todo and habit"""
    font_title = make_font(20)
    font_small = make_font(18)
    
    content_w = W - RIGHT_W - content_x
    col_w = content_w // 2
    row_h = H // 2
    
    # Filter: only todo and habit
    todo_events = [e for e in events if e.get("type") in ("todo", "habit")]
    
    for row in range(2):
        for col in range(2):
            idx = row * 2 + col
            label, importance, urgency = QUADRANT_LABELS[idx]
            x = content_x + col * col_w
            y = row * row_h
            
            draw.rectangle([(x, y), (x + col_w - 2, y + row_h - 2)], fill=248)
            draw.text((x + 10, y + 10), label, font=font_title, fill=0)
            
            quad_events = [e for e in todo_events
                         if e.get("importance") == importance
                         and e.get("urgency") == urgency]
            
            event_y = y + 40
            for ev in quad_events[:4]:
                title = ev.get("title", "")[:10]
                draw.text((x + 10, event_y), title, font=font_small, fill=0)
                event_y += 24

def render_settings_view(draw, content_x):
    """Settings view"""
    font_button = make_font(24)
    
    y = 50
    button_w = 200
    button_h = 35
    button_x = content_x + 50
    
    draw.rectangle([(button_x, y), (button_x + button_w, y + button_h)], fill=240)
    draw.text((button_x + 40, y + 5), "退出日历", font=font_button, fill=0)

def render_frame(view, date_str, events, output_path):
    """Main render function"""
    img = Image.new('L', (W, H), 255)
    draw = ImageDraw.Draw(img)
    
    show_left = (view == "home" or view == "day")
    
    if show_left:
        render_left_panel(draw)
        content_x = LEFT_W
    else:
        content_x = 0
    
    render_right_nav(draw, view)
    
    if view == "home":
        render_home_view(draw, events, content_x)
    elif view == "day":
        render_day_view(draw, date_str, events, content_x)
    elif view == "three_day":
        center_date = datetime.date.fromisoformat(date_str)
        events_by_date = group_events_by_date(events, center_date)
        render_three_day_view(draw, date_str, events_by_date, content_x, W - RIGHT_W - content_x)
    elif view == "list":
        render_todo_view(draw, events, content_x)
    elif view == "quadrant":
        render_quadrant_view(draw, events, content_x)
    elif view == "settings":
        render_settings_view(draw, content_x)
    
    img.save(output_path)