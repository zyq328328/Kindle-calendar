#!/usr/bin/env python3
"""
Kindle 本地 PIL 日历渲染器 - 竖版布局
600x800 竖屏
- 顶部导航栏：60px高，水平排列
- 主内容区：全宽，y=60 起
"""
import os, sys, json, datetime, urllib.request, functools
from PIL import Image, ImageDraw, ImageFont

SERVER_URL = os.environ.get("SERVER_URL", "http://192.168.10.7:8082/api/events")

# ========== 尺寸常量 ==========
W, H = 600, 800

# 顶部导航栏
NAV_H = 60
NAV_BG = 30       # 深灰黑背景
NAV_FG = 200      # 亮灰文字
NAV_ACTIVE = 0    # 选中项黑色

# 导航项（水平排列）
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

# 主内容区
MAIN_Y = NAV_H
MAIN_H = H - NAV_H  # 740

TOP_H = 80        # 顶部日期区高度（各视图内）

FONT_PATHS = [
    "/usr/java/lib/fonts/STHeitiMedium.ttf",
    "/usr/java/lib/fonts/CNHotel.ttf",
]


def find_font():
    for p in FONT_PATHS:
        if os.path.exists(p):
            return p
    return None


@functools.lru_cache(maxsize=16)
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


def get_priority_color(ev):
    """根据 importance + urgency 返回颜色（替代废弃的 priority 字段）"""
    imp = ev.get("importance", "not_important")
    urg = ev.get("urgency", "not_urgent")
    if imp == "important" and urg == "urgent":
        return 0      # 红色
    elif imp == "important":
        return 40     # 蓝色
    elif urg == "urgent":
        return 200    # 橙色
    return 160        # 灰色


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


# ========== 渲染：顶部导航栏 ==========

def render_nav_topbar(draw, active_view):
    """渲染顶部导航栏（水平排列）"""
    draw.rectangle([(0, 0), (W - 1, NAV_H - 1)], fill=NAV_BG)

    n = len(NAV_ITEMS)
    item_w = W // n  # 每个导航项宽度（约75px）
    now = datetime.datetime.now()

    for i, (label, view) in enumerate(NAV_ITEMS):
        x = i * item_w
        is_active = (view == active_view)

        if is_active:
            draw.rectangle([(x + 2, 2), (x + item_w - 2, NAV_H - 2)], fill=60)
            # 顶部高亮线
            draw.line([(x + 2, 0), (x + item_w - 2, 0)], fill=120, width=3)

        # 圆点
        cx = x + item_w // 2
        cy = NAV_H // 2 - 6
        if is_active:
            draw.ellipse([(cx - 3, cy), (cx + 3, cy + 6)], fill=255)

        draw.text((x + 4, NAV_H - 28), label, font=make_font(16), fill=NAV_FG if not is_active else 255)

    # 右侧时间
    draw.text((W - 56, NAV_H - 28), now.strftime("%H:%M"), font=make_font(14), fill=100)


def touch_to_view(x, y):
    """触摸坐标 → 视图名"""
    if y < NAV_H and y >= 0:
        n = len(NAV_ITEMS)
        item_w = W // n
        idx = x // item_w
        idx = max(0, min(idx, n - 1))
        return NAV_ITEMS[idx][1]
    return None  # 主内容区触摸不切换视图


# ========== 视图：首页 ==========

def render_home_view(draw, events):
    """首页：当前日期 + 今日概览"""
    font_title = make_font(52)
    font_medium = make_font(22)
    font_small = make_font(18)
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    wd = ["一","二","三","四","五","六","日"][now.weekday()]

    # 左侧大日期
    draw.text((20, 10), str(now.day), font=font_title, fill=0)
    draw.text((20, 65), now.strftime("%m月"), font=font_medium, fill=80)
    draw.text((20, 92), f"周{wd}", font=font_small, fill=100)

    # 分隔线
    draw.line([(130, 10), (130, TOP_H - 10)], fill=200, width=1)

    # 右侧统计
    today_evs = [e for e in events if e.get("date", "").startswith(today_str)]
    pending = [e for e in events if not e.get("completed")]
    urgent = [e for e in events
              if e.get("importance") == "important" and e.get("urgency") == "urgent" and not e.get("completed")]
    draw.text((140, 15), f"今日 {len(today_evs)}", font=font_small, fill=80)
    draw.text((140, 40), f"待办 {len(pending)}", font=font_small, fill=80)
    draw.text((140, 65), f"紧急 {len(urgent)}", font=font_small, fill=0)

    # 分割线
    draw.line([(10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    # 今日日程列表
    y = TOP_H + 10
    if not today_evs:
        draw.text((20, y + 20), "(今日无日程)", font=font_small, fill=180)
    else:
        for ev in today_evs[:10]:
            time_str = ev.get("time", "") or ""
            title = ev.get("title", "")[:16]
            color = get_priority_color(ev)
            draw.rectangle([(10, y + 2), (14, y + 26)], fill=color)
            text = f"{time_str} {title}" if time_str else f"    {title}"
            fill = 180 if ev.get("completed") else 0
            draw.text((22, y + 3), text, font=font_small, fill=fill)
            y += 30


# ========== 视图：日 ==========

def render_day_view(draw, date_str, events):
    """日视图：大日期 + 今日日程"""
    font_title = make_font(56)
    font_medium = make_font(22)
    font_small = make_font(18)
    d = datetime.date.fromisoformat(date_str)
    wd = ["一","二","三","四","五","六","日"][d.weekday()]

    # 左侧日期
    draw.text((20, 10), str(d.day), font=font_title, fill=0)
    draw.text((20, 70), d.strftime("%m月"), font=font_medium, fill=80)
    draw.text((20, 96), f"周{wd}", font=font_small, fill=100)

    # 分隔线
    draw.line([(130, 10), (130, TOP_H - 10)], fill=200, width=1)

    # 统计
    draw.text((140, 15), f"{len(events)} 项日程", font=font_small, fill=80)
    pending = [e for e in events if not e.get("completed")]
    draw.text((140, 40), f"未完成 {len(pending)}", font=font_small, fill=0)

    # 分割线
    draw.line([(10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    # 日程列表
    y = TOP_H + 10
    if not events:
        draw.text((20, y + 20), "(今日无日程)", font=font_small, fill=180)
    else:
        for ev in events[:12]:
            time_str = ev.get("time", "") or ""
            title = ev.get("title", "")[:16]
            color = get_priority_color(ev)
            draw.rectangle([(10, y + 2), (14, y + 26)], fill=color)
            text = f"{time_str} {title}" if time_str else f"    {title}"
            fill = 180 if ev.get("completed") else 0
            draw.text((22, y + 3), text, font=font_small, fill=fill)
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

    col_count = 3
    col_w = (W - 20) // col_count
    labels = ["昨天", "今天", "明天"]
    offsets = [-1, 0, 1]

    # 顶部月份
    draw.text((20, 8), center.strftime("%Y年 %m月"), font=font_tiny, fill=120)
    draw.line([(10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    for ci, (offset, label) in enumerate(zip(offsets, labels)):
        d = center + datetime.timedelta(days=offset)
        date_key = d.isoformat()
        events = events_by_date.get(date_key, [])
        x = 10 + ci * col_w
        is_today = offset == 0

        # 日期头背景
        bg = 230 if is_today else 245
        draw.rectangle([(x, TOP_H + 5), (x + col_w - 8, TOP_H + 55)], fill=bg)

        # 日期数字
        day_color = 0 if is_today else 60
        draw.text((x + 8, TOP_H + 8), str(d.day), font=font_large, fill=day_color)

        # 星期+日期
        wd = ["一","二","三","四","五","六","日"][d.weekday()]
        sub = f"周{wd} {d.month}/{d.day}"
        draw.text((x + 8, TOP_H + 38), sub, font=font_tiny, fill=100)

        # 列分隔线
        if ci < 2:
            draw.line([(x + col_w - 4, TOP_H + 5), (x + col_w - 4, H - 10)], fill=200, width=1)

        # 日程
        y = TOP_H + 62
        if not events:
            draw.text((x + 8, y + 5), "-", font=font_tiny, fill=180)
            y += 22
        else:
            for ev in events[:10]:
                time_str = ev.get("time", "")[:5] if ev.get("time") else ""
                title = ev.get("title", "")[:10]
                completed = ev.get("completed", False)
                color = get_priority_color(ev)

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

    draw.text((20, 10), "任务清单", font=font_medium, fill=0)
    draw.line([(10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    pending = [e for e in events if not e.get("completed")]
    done = [e for e in events if e.get("completed")]

    y = TOP_H + 12
    # 未完成区
    for ev in pending[:15]:
        time_str = ev.get("time", "") or ""
        title = ev.get("title", "")[:18]
        color = get_priority_color(ev)

        draw.rectangle([(10, y + 2), (24, y + 16)], outline=100, width=1)
        prefix = f"{time_str} " if time_str else "      "
        draw.text((30, y + 1), prefix + title, font=font_small, fill=0)
        draw.rectangle([(10, y + 2), (12, y + 16)], fill=color)
        y += 26

    if not pending:
        draw.text((20, y + 10), "(无待办)", font=font_small, fill=180)
        y += 32

    # 已完成区
    if done:
        y += 8
        draw.line([(10, y), (W - 10, y)], fill=200, width=1)
        draw.text((20, y + 6), f"已完成 ({len(done)})", font=font_small, fill=120)
        y += 28
        for ev in done[:8]:
            title = ev.get("title", "")[:18]
            draw.text((30, y + 1), title, font=font_small, fill=180)
            y += 24


# ========== 视图：四象限 ==========

def render_quadrant_view(draw, events):
    """四象限视图"""
    font_medium = make_font(18)
    font_small = make_font(15)

    draw.text((20, 10), "四象限", font=font_medium, fill=0)
    draw.line([(10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    todos = [e for e in events if e.get("type") in ("todo", "schedule") and not e.get("completed")]

    q1 = [e for e in todos if e.get("importance") == "important" and e.get("urgency") == "urgent"]
    q2 = [e for e in todos if e.get("importance") == "important" and e.get("urgency") == "not_urgent"]
    q3 = [e for e in todos if e.get("importance") == "not_important" and e.get("urgency") == "urgent"]
    q4 = [e for e in todos if e.get("importance") == "not_important" and e.get("urgency") == "not_urgent"]

    margin = 10
    gap = 8
    usable_w = W - margin * 2
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
        draw.rectangle([(qx, qy), (qx + qw, qy + qh)], fill=255)
        draw.rectangle([(qx, qy), (qx + qw, qy + 24)], fill=230)
        draw.text((qx + 6, qy + 4), label, font=font_small, fill=0)
        draw.text((qx + qw - 18, qy + 4), f"Q{qi}", font=font_small, fill=120)

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
    draw.text((20, 10), "习惯打卡", font=font_medium, fill=0)
    draw.text((140, 14), now.strftime("%m/%d"), font=font_small, fill=100)
    draw.line([(10, TOP_H), (W - 10, TOP_H)], fill=200, width=1)

    habits = [e for e in events if e.get("type") == "habit"]

    y = TOP_H + 12
    if not habits:
        draw.text((20, y + 30), "(暂无习惯)", font=font_small, fill=180)
    else:
        for ev in habits:
            title = ev.get("title", "")[:20]
            completed = ev.get("completed", False)
            ev_date = ev.get("date", "")

            draw.rectangle([(10, y), (W - 10, y + 38)], outline=220, width=1)
            draw.rectangle([(18, y + 9), (34, y + 25)], outline=100, width=1)
            if completed:
                draw.text((21, y + 9), "V", font=font_small, fill=0)
                fill = 180
            else:
                fill = 0

            draw.text((42, y + 10), title, font=font_small, fill=fill)
            if ev_date:
                draw.text((W - 80, y + 10), ev_date[5:], font=font_tiny, fill=120)

            y += 44
            if y > H - 30:
                break


# ========== 主渲染入口 ==========

def render_frame(view, date_str, events, out_path="/tmp/calendar_frame.png"):
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    # 渲染顶部导航
    render_nav_topbar(draw, view)

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
