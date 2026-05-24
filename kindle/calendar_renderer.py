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
    ("今日", "home"),
    ("单日", "day"),
    ("三日", "three_day"),
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


def _event_matches_date(ev, date_key):
    """Check if event should appear on given date (supports display_dates fallback)"""
    ev_date = ev.get("date", "")
    if ev_date.startswith(date_key):
        return True
    # 对于重复事件，display_dates 包含所有应出现的日期
    display_dates = ev.get("display_dates", [])
    if display_dates and date_key in display_dates:
        return True
    return False


def _is_event_completed(ev, all_events):
    """Check if event is completed across all its display dates.
    For multi-day todos, if completed on any date, it should show as completed on all dates."""
    # 如果当前事件已标记完成，直接返回True
    if ev.get("completed"):
        return True
    
    # 检查是否有其他同ID的事件在其他日期被标记为完成
    ev_id = ev.get("id")
    if not ev_id:
        return False
    
    display_dates = ev.get("display_dates", [])
    if not display_dates:
        return False
    
    # 查找同ID的其他事件实例
    for other_ev in all_events:
        if isinstance(other_ev, tuple):
            other_ev = other_ev[0]
        if other_ev.get("id") == ev_id and other_ev.get("completed"):
            return True
    
    return False


def flatten_tree(tree, depth=0):
    """将事件树展平为 (event, depth) 列表，用于带缩进的渲染"""
    result = []
    for ev in tree:
        result.append((ev, depth))
        if ev.get("children"):
            result.extend(flatten_tree(ev["children"], depth + 1))
    return result


def fetch_events(date_str=None, max_retries=3):
    """Fetch events (tree) with retry mechanism"""
    TREE_URL = SERVER_URL.replace("/api/events", "/api/events/tree")
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(TREE_URL)
            with urllib.request.urlopen(req, timeout=3) as resp:
                tree = json.loads(resp.read().decode())
                flat = flatten_tree(tree)
                if date_str:
                    return [(ev, depth) for ev, depth in flat if ev.get("date", "").startswith(date_str)]
                return flat
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
    
    font_time = make_font(50)
    font_day = make_font(88)
    font_ym = make_font(22)
    font_weekday = make_font(24)

    draw.text((15, 60), str(day), font=font_day, fill=0)
    draw.text((15, 160), f"{year}年{month:02d}月", font=font_ym, fill=0)
    draw.text((15, 190), weekday, font=font_weekday, fill=0)
    draw.text((15, 540), time_str, font=font_time, fill=0)

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
    
    day_events_raw = [(e, d) for e, d in events if _event_matches_date(e, date_str)]
    schedules_raw = [(e, d) for e, d in day_events_raw if e.get("type") == "schedule"]
    todos_raw = [(e, d) for e, d in day_events_raw if e.get("type") in ("todo", "habit")]
    
    # 日程 section
    draw.text((content_x + 20, y), "【日程】", font=font_section, fill=0)
    y += 30
    
    if not schedules_raw:
        draw.text((content_x + 30, y), "暂无日程", font=font_small, fill=150)
        y += 25
    else:
        for ev, depth in schedules_raw:
            indent = depth * 20
            time_str = ev.get("time", "")[:5]
            title = ev.get("title", "")[:14]
            if time_str:
                draw.text((content_x + 30 + indent, y), time_str, font=font_small, fill=80)
                draw.text((content_x + 85 + indent, y), title, font=font_small, fill=0)
            else:
                draw.text((content_x + 30 + indent, y), title, font=font_small, fill=0)
            y += 25
    
    y += 10
    
    # 待办 section
    draw.text((content_x + 20, y), "【待办】", font=font_section, fill=0)
    y += 30
    
    if not todos_raw:
        draw.text((content_x + 30, y), "暂无待办", font=font_small, fill=150)
    else:
        for ev, depth in todos_raw:
            indent = depth * 20
            title = ev.get("title", "")[:16]
            # 使用_is_event_completed检查完成状态（支持跨日期完成同步）
            completed = _is_event_completed(ev, events)
            box = "■" if completed else "□"
            box_fill = 120 if completed else 80
            title_fill = 150 if completed else 0
            draw.text((content_x + 30 + indent, y), box, font=font_small, fill=box_fill)
            draw.text((content_x + 52 + indent, y), title, font=font_small, fill=title_fill)
            y += 25

def render_home_view(draw, events, content_x):
    """Home view"""
    render_day_or_home_view(draw, None, events, content_x, is_home=True)

def render_day_view(draw, date_str, events, content_x):
    """Day view"""
    render_day_or_home_view(draw, date_str, events, content_x, is_home=False)

def group_events_by_date(events, center_date):
    """Group events by date from already fetched list (supports both flat and tree format)"""
    result = {}
    for offset in [-1, 0, 1]:
        d = center_date + datetime.timedelta(days=offset)
        date_key = d.isoformat()
        # events can be [(event, depth), ...] or [event, ...]
        if events and isinstance(events[0], tuple):
            result[date_key] = [(e, depth) for e, depth in events
                                if _event_matches_date(e, date_key)]
        else:
            result[date_key] = [e for e in events
                                if _event_matches_date(e, date_key)]
    return result


def render_three_day_view(draw, date_str, events_by_date, content_x=LEFT_W, content_w=None):
    """Three-day view: 3 columns of date + schedule"""
    font_date = make_font(22)
    font_small = make_font(20)
    font_section = make_font(20)
    
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
        
        # 日程 section（只看 schedule，深度扁平）
        y = 52
        draw.text((x + 3, y), "【日程】", font=font_section, fill=80)
        y += 30
        SCHED_H = 22
        sched_raw = [(e, d) for e, d in events if e.get("type") == "schedule"]
        for ev, depth in sched_raw:
            indent = depth * 12
            time_str = ev.get("time", "")[:5]
            title = ev.get("title", "")[:10]
            if time_str:
                draw.text((x + 6 + indent, y), time_str, font=font_small, fill=80)
                draw.text((x + 56 + indent, y), title, font=font_small, fill=0)
            else:
                draw.text((x + 3 + indent, y), title, font=font_small, fill=0)
            y += SCHED_H

        # 待办 section（显示所有 todo+habit，区分完成状态）
        y += 4
        draw.text((x + 3, y), "【待办】", font=font_section, fill=80)
        y += 30
        TODO_H = 22
        todo_raw = [(e, d) for e, d in events if e.get("type") in ("todo", "habit")]
        if not todo_raw:
            draw.text((x + 3, y), "□ 暂无待办", font=font_small, fill=140)
        else:
            for ev, depth in todo_raw:
                indent = depth * 12
                title = ev.get("title", "")[:11]
                # 使用_is_event_completed检查完成状态（支持跨日期完成同步）
                completed = _is_event_completed(ev, events)
                box = "■" if completed else "□"
                box_fill = 120 if completed else 80
                title_fill = 150 if completed else 0
                draw.text((x + 3 + indent, y), box, font=font_small, fill=box_fill)
                draw.text((x + 18 + indent, y), title, font=font_small, fill=title_fill)
                y += TODO_H
        
        # Column separator
        if i < len(dates) - 1:
            line_x = x + col_w - 3
            draw.line([(line_x, 5), (line_x, H - 10)], fill=200, width=1)
        
        x += col_w

def render_todo_view(draw, events, content_x):
    """Todo list view - only show uncompleted todos"""
    font_title = make_font(24)
    font_small = make_font(20)
    
    y = 20
    draw.text((content_x + 20, y), "待办列表", font=font_title, fill=0)
    y += 40
    
    # Support both flat [event] and tree [(event, depth)], filter out completed
    if events and isinstance(events[0], tuple):
        ev_list = [(e, depth) for e, depth in events 
                  if e.get("type") in ("todo", "habit") and not e.get("completed")]
    else:
        ev_list = [(e, 0) for e in events 
                  if e.get("type") in ("todo", "habit") and not e.get("completed")]
    
    def sort_key(item):
        ev, depth = item
        imp = 0 if ev.get("importance") == "important" else 1
        urg = 0 if ev.get("urgency") == "urgent" else 1
        return (imp, urg)
    
    ev_list.sort(key=sort_key)
    
    if not ev_list:
        draw.text((content_x + 20, y), "暂无待办", font=font_small, fill=100)
        return
    
    for ev, depth in ev_list:
        indent = depth * 20
        title = ev.get("title", "")[:16]
        # All items here are uncompleted
        draw.text((content_x + 20 + indent, y), "□", font=font_small, fill=80)
        draw.text((content_x + 42 + indent, y), title, font=font_small, fill=0)
        y += 28

QUADRANT_LABELS = [
    ("重要不紧急", "important", "not_urgent"),
    ("重要紧急", "important", "urgent"),
    ("不紧急不重要", "not_important", "not_urgent"),
    ("紧急不重要", "not_important", "urgent"),
]

def render_quadrant_view(draw, events, content_x):
    """Four quadrant view - only todo and habit, filter out completed"""
    font_title = make_font(20)
    font_small = make_font(18)
    
    content_w = W - RIGHT_W - content_x
    col_w = content_w // 2
    row_h = H // 2
    
    # Filter: only todo and habit, exclude completed (support both flat and tree format)
    if events and isinstance(events[0], tuple):
        todo_events = [(e, depth) for e, depth in events 
                      if e.get("type") in ("todo", "habit") and not e.get("completed")]
    else:
        todo_events = [(e, 0) for e in events 
                      if e.get("type") in ("todo", "habit") and not e.get("completed")]

    # Draw quadrant separators
    mid_x = content_x + col_w
    mid_y = row_h
    # Horizontal line (separates top/bottom rows)
    draw.line([(content_x, mid_y), (content_x + content_w, mid_y)], fill=0, width=2)
    # Vertical line (separates left/right columns)
    draw.line([(mid_x, 0), (mid_x, H)], fill=0, width=2)

    for row in range(2):
        for col in range(2):
            idx = row * 2 + col
            label, importance, urgency = QUADRANT_LABELS[idx]
            x = content_x + col * col_w
            y = row * row_h

            draw.text((x + 10, y + 10), label, font=font_title, fill=0)

            quad_events = [(e, depth) for e, depth in todo_events
                         if e.get("importance") == importance
                         and e.get("urgency") == urgency]

            event_y = y + 48
            for ev, depth in quad_events:
                indent = depth * 12
                title = ev.get("title", "")[:14]
                # All items here are uncompleted
                draw.text((x + 10 + indent, event_y), "□", font=font_small, fill=80)
                draw.text((x + 22 + indent, event_y), title, font=font_small, fill=0)
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