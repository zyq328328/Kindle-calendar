#!/usr/bin/env python3
"""
Kindle 本地 PIL 日历渲染器 - 新版左侧导航布局
800x600 横版
- 左侧导航栏：80px宽
- 右侧主内容区：720px宽
"""
import os, sys, json, datetime, urllib.request
from PIL import Image, ImageDraw, ImageFont

SERVER_URL = "http://192.168.10.7:8082/api/events"

# ========== 尺寸常量 ==========
W, H = 800, 600

# 左侧导航栏
NAV_W = 80
NAV_BG = 30       # 深灰黑背景
NAV_FG = 220      # 亮灰文字
NAV_ACTIVE = 0    # 选中项黑色
NAV_DIVIDER = 60  # 导航项目分隔

# 主内容区
MAIN_X = NAV_W
MAIN_W = W - NAV_W  # 720

TOP_H = 90        # 顶部日期区高度

# 导航项
NAV_ITEMS = [
    ("首", "home"),
    ("日", "day"),
    ("三", "three_day"),
    ("周", "week"),
    ("清", "list"),
    ("四", "quadrant"),
    ("习", "habit"),
    ("设", "settings"),
]

FONT_PATHS = [
    "/usr/java/lib/fonts/STHeitiMedium.ttf",
    "/usr/java/lib/fonts/CNHotel.ttf",
]


def find_font():
    for p in FONT_PATHS:
        if os.path.exists(p):
            return p
    return None


def make_font(size):
    try:
        return ImageFont.truetype(find_font(), size)
    except Exception:
        return ImageFont.load_default()


def tb(font, text):
    """text bounding box width"""
    try:
        return font.getbbox(text)[2]
    except Exception:
        return 0


def fetch_events(date_str=None):
    try:
        req = urllib.request.Request(SERVER_URL)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if date_str:
                return [e for e in data if e.get("date", "").startswith(date_str)]
            return data
    except Exception as e:
        print(f"[renderer] fetch failed: {e}")
        return []


# ========== 渲染：左侧导航栏 ==========

def render_nav_sidebar(draw, active_view):
    """渲染左侧导航栏"""
    draw.rectangle([(0, 0), (NAV_W - 1, H)], fill=NAV_BG)

    item_h = 52
    start_y = 10
    for i, (label, view) in enumerate(NAV_ITEMS):
        y = start_y + i * item_h
        if view == "home":
            # 顶部标题
            draw.rectangle([(4, 4), (NAV_W - 4, 36)], fill=60)
            draw.text((14, 8), "历", font=make_font(20), fill=255)
            continue

        is_active = (view == active_view)
        bg = 60 if is_active else NAV_BG
        draw.rectangle([(4, y + 2), (NAV_W - 4, y + item_h - 2)], fill=bg)

        # 圆点指示
        dot_x = 10
        dot_y = y + item_h // 2 - 3
        if is_active:
            draw.ellipse([(dot_x, dot_y), (dot_x + 6, dot_y + 6)], fill=255)

        draw.text((22, y + 14), label, font=make_font(18), fill=NAV_FG if not is_active else 255)

    # 底部时间
    now = datetime.datetime.now()
    draw.text((8, H - 40), now.strftime("%H:%M"), font=make_font(16), fill=100)


def touch_to_view(x, y):
    """触摸坐标 → 视图名"""
    if x < NAV_W:
        # 左侧导航栏
        idx = (y - 10) // 52
        idx = max(0, min(idx, len(NAV_ITEMS) - 1))
        return NAV_ITEMS[idx][1]
    return None  # 主内容区触摸不切换视图


# ========== 视图：首页 ==========

def render_home_view(draw, events):
    """首页：当前日期 + 今日概览"""
    font_title = make_font(40)
    font_medium = make_font(22)
    font_small = make_font(18)
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    wd = ["一","二","三","四","五","六","日"][now.weekday()]

    # 日期大字
    day_str = str(now.day)
    draw.text((MAIN_X + 20, 10), day_str, font=font_title, fill=0)
    draw.text((MAIN_X + 20, 55), now.strftime("%m月"), font=font_medium, fill=80)
    draw.text((MAIN_X + 20, 80), f"周{wd}", font=font_small, fill=100)

    # 分隔线
    draw.line([(MAIN_X + 120, 10), (MAIN_X + 120, TOP_H - 10)], fill=200, width=1)

    # 右侧统计
    today_evs = [e for e in events if e.get("date", "").startswith(today_str)]
    pending = [e for e in events if not e.get("completed")]
    urgent = [e for e in events if e.get("priority") == "urgent" and not e.get("completed")]
    draw.text((MAIN_X + 130, 15), f"今日 {len(today_evs)}", font=font_small, fill=80)
    draw.text((MAIN_X + 130, 40), f"待办 {len(pending)}", font=font_small, fill=80)
    draw.text((MAIN_X + 130, 65), f"紧急 {len(urgent)}", font=font_small, fill=0)

    # 分割线
    draw.line([(MAIN_X + 10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    # 今日日程列表
    y = TOP_H + 10
    if not today_evs:
        draw.text((MAIN_X + 20, y + 20), "(今日无日程)", font=font_small, fill=180)
    else:
        for ev in today_evs[:10]:
            time_str = ev.get("time", "") or ""
            title = ev.get("title", "")[:16]
            priority = ev.get("priority", "normal")
            color = {"urgent": 0, "important": 40, "normal": 160}[priority]

            # 左侧色条
            draw.rectangle([(MAIN_X + 10, y + 2), (MAIN_X + 14, y + 26)], fill=color)
            text = f"{time_str} {title}" if time_str else f"    {title}"
            fill = 180 if ev.get("completed") else 0
            draw.text((MAIN_X + 22, y + 3), text, font=font_small, fill=fill)
            y += 30


# ========== 视图：日 ==========

def render_day_view(draw, date_str, events):
    """日视图：大日期 + 今日日程"""
    font_title = make_font(52)
    font_medium = make_font(22)
    font_small = make_font(18)
    d = datetime.date.fromisoformat(date_str)
    wd = ["一","二","三","四","五","六","日"][d.weekday()]

    # 左上角日期
    draw.text((MAIN_X + 20, 10), str(d.day), font=font_title, fill=0)
    draw.text((MAIN_X + 20, 65), d.strftime("%m月"), font=font_medium, fill=80)
    draw.text((MAIN_X + 20, 90), f"周{wd}", font=font_small, fill=100)

    # 分隔线
    draw.line([(MAIN_X + 130, 10), (MAIN_X + 130, TOP_H - 10)], fill=200, width=1)

    # 今日日程数量统计
    draw.text((MAIN_X + 140, 15), f"{len(events)} 项日程", font=font_small, fill=80)
    pending = [e for e in events if not e.get("completed")]
    draw.text((MAIN_X + 140, 40), f"未完成 {len(pending)}", font=font_small, fill=0)

    # 分割线
    draw.line([(MAIN_X + 10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    # 日程列表
    y = TOP_H + 10
    if not events:
        draw.text((MAIN_X + 20, y + 20), "(今日无日程)", font=font_small, fill=180)
    else:
        for ev in events[:12]:
            time_str = ev.get("time", "") or ""
            title = ev.get("title", "")[:16]
            priority = ev.get("priority", "normal")
            color = {"urgent": 0, "important": 40, "normal": 160}[priority]

            draw.rectangle([(MAIN_X + 10, y + 2), (MAIN_X + 14, y + 26)], fill=color)
            text = f"{time_str} {title}" if time_str else f"    {title}"
            fill = 180 if ev.get("completed") else 0
            draw.text((MAIN_X + 22, y + 3), text, font=font_small, fill=fill)
            y += 30


# ========== 视图：三 ==========

def fetch_three_day_events(center_date):
    result = {}
    for offset in [-1, 0, 1]:
        d = center_date + datetime.timedelta(days=offset)
        result[d.isoformat()] = fetch_events(d.isoformat())
    return result


def render_three_day_view(draw, date_str, events_by_date):
    """三日视图：3列日期+日程"""
    font_large = make_font(28)
    font_small = make_font(16)
    font_tiny = make_font(14)

    now = datetime.datetime.now()
    center = datetime.date.fromisoformat(date_str)

    col_w = (MAIN_W - 20) // 3
    labels = ["昨天", "今天", "明天"]
    offsets = [-1, 0, 1]

    # 顶部月份小字
    draw.text((MAIN_X + 20, 8), center.strftime("%Y年 %m月"), font=font_tiny, fill=120)
    draw.line([(MAIN_X + 10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    for ci, (offset, label) in enumerate(zip(offsets, labels)):
        d = center + datetime.timedelta(days=offset)
        date_key = d.isoformat()
        events = events_by_date.get(date_key, [])
        x = MAIN_X + 10 + ci * col_w
        is_today = offset == 0

        # 日期头背景
        bg = 230 if is_today else 245
        draw.rectangle([(x, TOP_H + 5), (x + col_w - 10, TOP_H + 55)], fill=bg)

        # 日期数字
        day_color = 0 if is_today else 60
        draw.text((x + 10, TOP_H + 8), str(d.day), font=font_large, fill=day_color)

        # 星期+日期
        wd = ["一","二","三","四","五","六","日"][d.weekday()]
        sub = f"周{wd} {d.month}/{d.day}"
        draw.text((x + 10, TOP_H + 38), sub, font=font_tiny, fill=100)

        # 列分隔线
        if ci < 2:
            draw.line([(x + col_w - 5, TOP_H + 5), (x + col_w - 5, H - 10)], fill=200, width=1)

        # 日程
        y = TOP_H + 62
        if not events:
            draw.text((x + 10, y + 5), "-", font=font_tiny, fill=180)
            y += 22
        else:
            for ev in events[:10]:
                time_str = ev.get("time", "")[:5] if ev.get("time") else ""
                title = ev.get("title", "")[:10]
                completed = ev.get("completed", False)
                priority = ev.get("priority", "normal")
                color = {"urgent": 0, "important": 50, "normal": 140}[priority]

                # 优先级色条
                draw.rectangle([(x + 4, y + 2), (x + 8, y + 20)], fill=color)

                if time_str:
                    draw.text((x + 12, y + 2), time_str, font=font_tiny, fill=120)
                    draw.text((x + 54, y + 2), title, font=font_tiny, fill=180 if completed else 0)
                else:
                    draw.text((x + 12, y + 2), title, font=font_tiny, fill=180 if completed else 0)
                y += 22


# ========== 视图：清单 ==========

def render_list_view(draw, events):
    """任务清单视图"""
    font_medium = make_font(20)
    font_small = make_font(16)

    draw.text((MAIN_X + 20, 10), "任务清单", font=font_medium, fill=0)
    draw.line([(MAIN_X + 10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    # 分组
    pending = [e for e in events if not e.get("completed")]
    done = [e for e in events if e.get("completed")]

    y = TOP_H + 12
    # 未完成区
    for ev in pending[:15]:
        time_str = ev.get("time", "") or ""
        title = ev.get("title", "")[:18]
        priority = ev.get("priority", "normal")
        color = {"urgent": 0, "important": 40, "normal": 160}[priority]

        # checkbox方框
        draw.rectangle([(MAIN_X + 10, y + 2), (MAIN_X + 24, y + 16)], outline=100, width=1)
        # 时间+标题
        prefix = f"{time_str} " if time_str else "      "
        draw.text((MAIN_X + 30, y + 1), prefix + title, font=font_small, fill=0)
        draw.rectangle([(MAIN_X + 10, y + 2), (MAIN_X + 12, y + 16)], fill=color)  # 优先级色条
        y += 26

    if not pending:
        draw.text((MAIN_X + 20, y + 10), "(无待办)", font=font_small, fill=180)
        y += 32

    # 已完成区
    if done:
        y += 8
        draw.line([(MAIN_X + 10, y), (W - 10, y)], fill=200, width=1)
        draw.text((MAIN_X + 20, y + 6), f"已完成 ({len(done)})", font=font_small, fill=120)
        y += 28
        for ev in done[:8]:
            title = ev.get("title", "")[:18]
            draw.text((MAIN_X + 30, y + 1), title, font=font_small, fill=180)
            y += 24


# ========== 视图：四象限 ==========

def render_quadrant_view(draw, events):
    """四象限视图"""
    font_medium = make_font(18)
    font_small = make_font(15)

    draw.text((MAIN_X + 20, 10), "四象限", font=font_medium, fill=0)
    draw.line([(MAIN_X + 10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    todos = [e for e in events if e.get("type") in ("todo", "schedule") and not e.get("completed")]

    # 四象限：importance × urgency
    q1 = [e for e in todos if e.get("importance") == "important" and e.get("urgency") == "urgent"]          # 重要+紧急
    q2 = [e for e in todos if e.get("importance") == "important" and e.get("urgency") == "not_urgent"]     # 重要+非紧急
    q3 = [e for e in todos if e.get("importance") == "not_important" and e.get("urgency") == "urgent"]      # 非重要+紧急
    q4 = [e for e in todos if e.get("importance") == "not_important" and e.get("urgency") == "not_urgent"]  # 非重要+非紧急

    margin = MAIN_X + 10
    gap = 8
    usable_w = W - margin - 10
    usable_h = H - TOP_H - 15
    half_w = (usable_w - gap) // 2
    half_h = (usable_h - gap) // 2

    quadrants = [
        (q1, "Q1 重要且紧急", 1, margin, TOP_H + 10, half_w, half_h, 0),
        (q2, "Q2 重要非紧急", 2, margin + half_w + gap, TOP_H + 10, half_w, half_h, 30),
        (q3, "Q3 紧急非重要", 3, margin, TOP_H + 10 + half_h + gap, half_w, half_h, 200),
        (q4, "Q4 非紧急非重要", 4, margin + half_w + gap, TOP_H + 10 + half_h + gap, half_w, half_h, 180),
    ]

    for items, label, qi, qx, qy, qw, qh, hdr_color in quadrants:
        # 背景
        draw.rectangle([(qx, qy), (qx + qw, qy + qh)], fill=255)
        # 标题栏
        draw.rectangle([(qx, qy), (qx + qw, qy + 24)], fill=230)
        draw.text((qx + 6, qy + 4), label, font=font_small, fill=0)
        # 象限编号
        draw.text((qx + qw - 18, qy + 4), f"Q{qi}", font=font_small, fill=120)

        # 列表
        y = qy + 30
        if not items:
            try:
                tw = tb(font_small, "(空)")
                draw.text((qx + (qw - tw) // 2, y + 20), "(空)", font=font_small, fill=180)
            except Exception:
                pass
        else:
            for ev in items[:7]:
                title = ev.get("title", "")[:14]
                time_str = ev.get("time", "") or ev.get("date", "")[5:] or ""
                draw.rectangle([(qx + 4, y + 2), (qx + 8, y + 16)], fill=hdr_color)
                draw.text((qx + 14, y + 1), title, font=font_small, fill=0)
                if time_str:
                    tw = tb(font_small, time_str)
                    draw.text((qx + qw - tw - 6, y + 1), time_str, font=font_small, fill=120)
                y += 20

    # 中心十字分隔线
    mid_x = margin + half_w + gap // 2
    mid_y = TOP_H + 10 + half_h
    draw.line([(mid_x, TOP_H + 10), (mid_x, H - 10)], fill=160, width=1)
    draw.line([(margin, mid_y), (W - 10, mid_y)], fill=160, width=1)
    draw.text((mid_x - 5, mid_y - 8), "+", font=make_font(14), fill=140)


# ========== 视图：习惯 ==========

def render_habit_view(draw, events):
    """习惯打卡视图"""
    font_medium = make_font(20)
    font_small = make_font(16)
    font_tiny = make_font(14)

    now = datetime.datetime.now()
    draw.text((MAIN_X + 20, 10), "习惯打卡", font=font_medium, fill=0)
    draw.text((MAIN_X + 140, 14), now.strftime("%m/%d"), font=font_small, fill=100)
    draw.line([(MAIN_X + 10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    habits = [e for e in events if e.get("type") == "habit"]
    today_str = now.strftime("%Y-%m-%d")

    y = TOP_H + 12
    if not habits:
        draw.text((MAIN_X + 20, y + 30), "(暂无习惯)", font=font_small, fill=180)
    else:
        for ev in habits:
            title = ev.get("title", "")[:20]
            completed = ev.get("completed", False)
            ev_date = ev.get("date", "")

            # 行背景
            draw.rectangle([(MAIN_X + 10, y), (W - 10, y + 38)], outline=220, width=1)

            # checkbox
            draw.rectangle([(MAIN_X + 18, y + 9), (MAIN_X + 34, y + 25)], outline=100, width=1)
            if completed:
                draw.text((MAIN_X + 21, y + 9), "V", font=font_small, fill=0)
                fill = 180
            else:
                fill = 0

            # 标题
            draw.text((MAIN_X + 42, y + 10), title, font=font_small, fill=fill)

            # 日期
            if ev_date:
                draw.text((MAIN_X + MAIN_W - 80, y + 10), ev_date[5:], font=font_tiny, fill=120)

            y += 44
            if y > H - 30:
                break


# ========== 主渲染入口 ==========

def render_frame(view, date_str, events, out_path="/tmp/calendar_frame.png"):
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    # 渲染左侧导航
    render_nav_sidebar(draw, view)

    # 渲染主内容区
    if view == "home":
        render_home_view(draw, events)
    elif view == "day":
        render_day_view(draw, date_str, events)
    elif view == "three_day":
        d = datetime.date.fromisoformat(date_str)
        evs_by_date = fetch_three_day_events(d)
        render_three_day_view(draw, date_str, evs_by_date)
    elif view == "list":
        render_list_view(draw, events)
    elif view == "quadrant":
        render_quadrant_view(draw, events)
    elif view == "habit":
        render_habit_view(draw, events)
    else:
        render_day_view(draw, date_str, events)

    img.save(out_path, "PNG")
    return True


if __name__ == "__main__":
    view = sys.argv[1] if len(sys.argv) > 1 else "day"
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().isoformat()
    out_path = sys.argv[3] if len(sys.argv) > 3 else "/tmp/calendar_frame.png"

    events = fetch_events()
    ok = render_frame(view, date_str, events, out_path)
    print(f"[renderer] {'OK' if ok else 'FAIL'} {view} {date_str} → {out_path}")
