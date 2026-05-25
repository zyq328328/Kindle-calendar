import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from datetime import datetime, timedelta

from models import EventCreate, EventUpdate, Event, SyncResponse, EventTreeItem
from database import (
    get_all_events, get_events_since, get_event_by_id,
    create_event, update_event, delete_event, get_server_time,
    get_events_in_range, get_event_tree
)

app = FastAPI(title="Kindle Calendar API", version="1.0.0")

# 静态文件（Vue 构建产物）
DIST_DIR = "/opt/kindle-calendar/web/dist"
if os.path.exists(DIST_DIR):
    app.mount("/static", StaticFiles(directory=DIST_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "ok", "service": "Kindle Calendar API"}

@app.get("/api/health")
def health():
    return {"status": "healthy", "server_time": get_server_time()}

@app.get("/api/events", response_model=list[Event])
def list_events(start: Optional[str] = None, end: Optional[str] = None):
    if start and end:
        events = get_events_in_range(start, end)
    else:
        events = get_all_events()
    return [serialize_event(e) for e in events]

@app.get("/api/events/tree")
def list_event_tree():
    """获取事件树：顶级任务 + 嵌套的 children（含缩进层级）"""
    tree = get_event_tree()
    for e in tree:
        serialize_event(e)
        for c in e.get("children", []):
            serialize_event(c)
    return tree

@app.post("/api/events", response_model=Event, status_code=201)
def create(event: EventCreate):
    event_data = event.model_dump()
    created = create_event(event_data)
    if created:
        return serialize_event(created)
    raise HTTPException(status_code=500, detail="Failed to create event")

@app.get("/api/events/{event_id}", response_model=Event)
def get_event(event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return serialize_event(event)

@app.put("/api/events/{event_id}", response_model=Event)
def modify_event(event_id: int, event: EventUpdate):
    existing = get_event_by_id(event_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    update_data = event.model_dump(exclude_unset=True)
    updated = update_event(event_id, update_data)
    if updated:
        return serialize_event(updated)
    raise HTTPException(status_code=500, detail="Failed to update event")

@app.delete("/api/events/{event_id}")
def remove_event(event_id: int):
    if not delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted", "id": event_id}

@app.post("/api/habits/{event_id}/checkin")
def habit_checkin(event_id: int, date: str):
    """习惯打卡：更新 last_completed_date（用于标记某天已完成）"""
    # 验证日期格式
    try:
        from datetime import datetime
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    ev = get_event_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Habit not found")
    if ev.get("type") != "habit":
        raise HTTPException(status_code=400, detail="Not a habit")
    updated = update_event(event_id, {"last_completed_date": date})
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")
    return serialize_event(updated)

@app.post("/api/habits/{event_id}/uncheck")
def habit_uncheck(event_id: int, date: str):
    """取消习惯打卡：清空 last_completed_date"""
    # 验证日期格式
    try:
        from datetime import datetime
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    ev = get_event_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Habit not found")
    if ev.get("type") != "habit":
        raise HTTPException(status_code=400, detail="Not a habit")
    updated = update_event(event_id, {"last_completed_date": None})
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")
    return serialize_event(updated)

@app.get("/api/sync", response_model=SyncResponse)
def sync(since: Optional[str] = None):
    if since:
        events = get_events_since(since)
    else:
        events = get_all_events()
    return SyncResponse(events=[serialize_event(e) for e in events], server_time=get_server_time())

# === Kindle Calendar Display Endpoints ===

import io
import struct
import os
import time
import threading
import subprocess
import logging
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from fastapi.responses import Response

# 配置日志，让 print 输出到 uvicorn stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
W, H = 800, 600  # 横版 landscape
TAB_Y = 520       # Tab bar 顶部（内容区 0~520）
TAB_H = 80        # Tab bar 高度（80px，屏幕约 1/7）
TAB_NAMES = ["日", "3日", "待办", "习惯"]
TAB_X = [0, 200, 400, 600]  # 各 tab 左边界

# 全局状态
current_view = "day"
calendar_active = False
display_loop_running = False
_stop_event = threading.Event()  # 用于可中断的 sleep
_state_lock = threading.Lock()
KINDLE_HOST = os.environ.get("KINDLE_HOST", "192.168.10.72")
KINDLE_KEY = os.environ.get("KINDLE_KEY", "C:/Users/Alex/Desktop/kindle_key")


def serialize_event(e: dict) -> dict:
    """将 SQLite 返回的 INTEGER 布尔值转为 Python bool（不修改原 dict）"""
    return {
        **e,
        "is_countdown": bool(e["is_countdown"]),
        "completed": bool(e["completed"]),
    }


def tb(font, text):
    """text bounding box: returns (width, height)"""
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return 0, 0


def render_frame(view: str) -> bytes:
    """渲染指定视图，返回 PNG bytes"""
    img = PIL.Image.new("L", (W, H), 255)
    draw = PIL.ImageDraw.Draw(img)

    try:
        font_title = PIL.ImageFont.truetype(FONT_PATH, 32)
        font_date  = PIL.ImageFont.truetype(FONT_PATH, 120)
        font_medium = PIL.ImageFont.truetype(FONT_PATH, 28)
        font_small = PIL.ImageFont.truetype(FONT_PATH, 20)
        font_tiny = PIL.ImageFont.truetype(FONT_PATH, 16)
        font_time  = PIL.ImageFont.truetype(FONT_PATH, 56)
        font_tab   = PIL.ImageFont.truetype(FONT_PATH, 24)
    except Exception:
        font_title = font_date = font_medium = font_small = font_time = font_tab = None

    now = datetime.now()

    # === 渲染内容区 ===
    if view == "day":
        _render_day_view(draw, now, font_date, font_medium, font_small, font_time)
    elif view == "week":
        _render_three_day_view(draw, now, font_tiny, font_small, font_medium, font_title)
    elif view == "todo":
        _render_todo_view(draw, now, font_small, font_medium)
    elif view == "habit":
        _render_habit_view(draw, now, font_small, font_medium)
    else:
        _render_day_view(draw, now, font_date, font_medium, font_small, font_time)

    # === 渲染 Tab bar ===
    _render_tab_bar(draw, view, font_tab)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_day_view(draw, now, font_date, font_medium, font_small, font_time):
    """日视图：左列日期时间 + 右列今日日程"""
    # 左列：时间 + 日期大字 + 年月 + 星期
    time_str = now.strftime("%H:%M")  # 无秒
    bw, bh = tb(font_time, time_str)
    draw.text((40, 20), time_str, fill=0, font=font_time)

    date_str = now.strftime("%d")
    bw, bh = tb(font_date, date_str)
    draw.text((40, 80), date_str, fill=0, font=font_date)

    ym = now.strftime("%Y年 %m月")
    draw.text((50, 210), ym, fill=80, font=font_medium)

    wd = ["一","二","三","四","五","六","日"][now.weekday()]
    draw.text((50, 250), f"星期{wd}", fill=80, font=font_medium)

    # 分隔线
    draw.line([(370, 20), (370, TAB_Y - 10)], fill=160, width=2)

    # 右列：今日日程
    today = now.strftime("%Y-%m-%d")
    events = get_events_in_range(today, today)
    y = 30
    for ev in events:
        t = ev.get("time", "")
        title = ev.get("title", "")[:16]
        completed = ev.get("completed", False)
        box = "■" if completed else "□"
        box_fill = 120 if completed else 60
        title_fill = 150 if completed else 0
        line = f"{t}  {box} {title}" if t else f"     {box} {title}"
        draw.text((390, y), line, fill=title_fill, font=font_small)
        y += 28
    if not events:
        draw.text((390, y), "(今日无日程)", fill=120, font=font_small)


def _render_three_day_view(draw, now, font_tiny, font_small, font_medium, font_title):
    """3日视图：横向排列 today + 未来2天，每天一列
    布局：顶部月份横幅 → 3列日期+星期+日程
    """
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_str = now.strftime("%Y年 %m月")
    draw.text((20, 8), month_str, fill=0, font=font_title)

    # 3列：每列宽 257px，左边 14px，中间 2*3=6px 分隔线，总计 14+3*257+6=791px
    COL_W = 257
    COL_GAP = 3
    COL_X = [14 + i * (COL_W + COL_GAP) for i in range(3)]
    HEADER_Y = 52   # 日期区顶部
    EV_Y = 105     # 日程区顶部
    EV_H = 20      # 每行高度
    MAX_EVS = 20   # 最多显示20行
    DAY_RANGE = 3  # 显示天数

    for i in range(DAY_RANGE):
        day = today + timedelta(days=i)
        x = COL_X[i]
        is_today = (i == 0)

        # 今日高亮背景
        if is_today:
            draw.rectangle([(x, 0), (x + COL_W - 1, TAB_Y - 1)], outline=0, width=2)

        # 日期数字大字
        day_num = day.strftime("%d")
        bw, bh = tb(font_medium, day_num)
        tx = x + (COL_W - bw) // 2
        draw.text((tx, HEADER_Y), day_num, fill=0 if is_today else 60, font=font_medium)

        # 星期
        wd = ["一","二","三","四","五","六","日"][day.weekday()]
        wd_str = f"周{wd}"
        bw, bh = tb(font_small, wd_str)
        tx = x + (COL_W - bw) // 2
        draw.text((tx, HEADER_Y + 42), wd_str, fill=80, font=font_small)

        # 星期下面小字：月/日
        md_str = day.strftime("%m/%d")
        bw, bh = tb(font_small, md_str)
        tx = x + (COL_W - bw) // 2
        draw.text((tx, HEADER_Y + 64), md_str, fill=120, font=font_small)

        # 日程（tiny 字体，充分利用列宽）
        date_str = day.strftime("%Y-%m-%d")
        day_events = [e for e in get_all_events() if e.get("date", "").startswith(date_str)]
        y = EV_Y
        for ev in day_events[:MAX_EVS]:
            t = ev.get("time", "")[:5]
            title = ev.get("title", "")[:18]
            completed = ev.get("completed", False)
            box = "■" if completed else "□"
            line = f"{t} {box}{title}" if t else f"  {box}{title}"
            fill = 150 if completed else (0 if is_today else 50)
            draw.text((x + 1, y), line, fill=fill, font=font_tiny)
            y += EV_H
        if not day_events:
            draw.text((x + 1, y), "-", fill=140, font=font_tiny)
        elif len(day_events) > MAX_EVS:
            draw.text((x + 1, y), f"+{len(day_events) - MAX_EVS}", fill=120, font=font_tiny)

        # 列分隔线
        if i < 2:
            sep_x = x + COL_W + COL_GAP // 2
            draw.line([(sep_x, 0), (sep_x, TAB_Y - 1)], fill=180, width=1)


def _render_todo_view(draw, now, font_small, font_medium):
    """待办视图：未完成 + 优先级"""
    draw.text((30, 20), "待办清单", fill=0, font=font_medium)

    today = now.strftime("%Y-%m-%d")
    all_events = get_events_in_range(today, today)
    todos = [e for e in all_events if e.get("type") in ("todo", "habit") and not e.get("completed")]
    todos.sort(key=lambda e: (
        0 if e.get("importance") == "important" and e.get("urgency") == "urgent" else
        1 if e.get("importance") == "important" and e.get("urgency") == "not_urgent" else
        2 if e.get("importance") == "not_important" and e.get("urgency") == "urgent" else 3
    ))

    y = 70
    for ev in todos[:12]:
        box = "□"
        imp = ev.get("importance", "not_important")
        urg = ev.get("urgency", "not_urgent")
        if imp == "important" and urg == "urgent":
            p_mark = "Q1"
        elif imp == "important" and urg == "not_urgent":
            p_mark = "Q2"
        elif imp == "not_important" and urg == "urgent":
            p_mark = "Q3"
        else:
            p_mark = "Q4"
        title = ev.get("title", "")[:16]
        date = ev.get("date", "")[5:]
        line = f"[{p_mark}] {date} {box} {title}"
        fill = 0 if imp == "important" and urg == "urgent" else (30 if imp == "important" else (60 if urg == "urgent" else 120))
        draw.text((30, y), line, fill=fill, font=font_small)
        y += 28
    if not todos:
        draw.text((30, y), "(暂无待办)", fill=120, font=font_small)


def _render_habit_view(draw, now, font_small, font_medium):
    """习惯视图：占位"""
    draw.text((30, 20), "习惯打卡", fill=0, font=font_medium)
    draw.text((30, 80), "(习惯功能开发中)", fill=140, font=font_small)
    draw.text((30, 115), "Phase 1 待实现", fill=120, font=font_small)


def _render_tab_bar(draw, active_view: str, font_tab):
    """底部 Tab bar"""
    view_idx = {"day": 0, "week": 1, "todo": 2, "habit": 3}[active_view]

    # Tab 背景
    draw.rectangle([(0, TAB_Y), (W, H)], fill=220)

    # 分隔线
    draw.line([(0, TAB_Y), (W, TAB_Y)], fill=160, width=2)

    for i, name in enumerate(TAB_NAMES):
        x = TAB_X[i]
        fill = 0 if i == view_idx else 100
        bw, bh = tb(font_tab, name)
        tx = x + (200 - bw) // 2
        ty = TAB_Y + (TAB_H - bh) // 2
        draw.text((tx, ty), name, fill=fill, font=font_tab)


def push_frame_to_kindle(png_bytes: bytes):
    """将 PNG 推送到 Kindle 屏幕（旋转后显示）"""
    # 本地旋转
    img = PIL.Image.open(io.BytesIO(png_bytes))
    rotated = img.rotate(-90, expand=True)

    local_path = "/tmp/cal_frame_kindle.png"
    rotated.save(local_path)

    # SCP 传到 Kindle
    subprocess.run([
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, local_path,
        f"root@{KINDLE_HOST}:/tmp/cal_frame_kindle.png"
    ], check=True, capture_output=True)

    # 显示（GC16 全屏刷新，清残影）
    subprocess.run([
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, f"root@{KINDLE_HOST}",
        "killall -STOP cvm; eips -c; eips -g /tmp/cal_frame_kindle.png -w GC16 -f; killall -CONT cvm"
    ], check=True, capture_output=True)


def push_frame_to_kindle_partial(png_bytes: bytes):
    """局部刷新：不清残影，不 STOP cvm，直接 eips 显示"""
    img = PIL.Image.open(io.BytesIO(png_bytes))
    rotated = img.rotate(-90, expand=True)
    local_path = "/tmp/cal_frame_kindle.png"
    rotated.save(local_path)

    # SCP 传图
    subprocess.run([
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, local_path,
        f"root@{KINDLE_HOST}:/tmp/cal_frame_kindle.png"
    ], check=True, capture_output=True)

    # 只 eips 显示，不 eips -c 清屏，不 STOP cvm
    subprocess.run([
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, f"root@{KINDLE_HOST}",
        "eips -g /tmp/cal_frame_kindle.png"
    ], check=True, capture_output=True)


def read_touch_from_kindle() -> str:
    """
    SIGSTOP cvm → 清空 event1 缓冲区 → 等待一次有效触摸 → 解析 tab 区域触摸 → 返回视图名
    无触摸或失败返回当前视图（不切换）
    """
    try:
        # 清空残留 + 停止 cvm（合并到一个 SSH 命令）
        # 顺序：先 flush 缓冲区（丢弃旧事件）→ sleep → 等待新事件（3秒超时）
        # 用 timeout 确保 cat 不会永久阻塞；无论是否读到事件，都要 CONT cvm
        r = subprocess.run([
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-i", KINDLE_KEY, f"root@{KINDLE_HOST}",
            "trap 'killall -CONT cvm 2>/dev/null; exit 0' EXIT; "  # 确保退出时 CONT
            "killall -STOP cvm; "
            "dd if=/dev/input/event1 bs=16 count=50 of=/dev/null 2>/dev/null; "
            "sleep 1.25; "
            "timeout 3 cat /dev/input/event1; "
            "killall -CONT cvm"
        ], capture_output=True, timeout=10)

        raw = r.stdout

        if not raw:
            logging.info("[touch] no data from event1")
            return current_view

        # 解析 event1：16字节 struct input_event (Linux)
        # ABS_MT_TRACKING_ID=57 (code), value=0xffffffff = 抬起
        touches = []
        touch = {}
        for i in range(0, len(raw), 16):
            chunk = raw[i:i+16]
            if len(chunk) < 16:
                break
            _, _, ev_type, code, value = struct.unpack('iiHHi', chunk)
            if ev_type == 3 and code == 57:  # ABS_MT_TRACKING_ID
                if value == 0xffffffff:  # 抬起，保存当前 touch
                    if touch and "x" in touch and "y" in touch:
                        touches.append(touch)
                    touch = {}
                else:
                    touch = {"id": value}
            elif ev_type == 3 and code == 54 and touch:  # ABS_MT_POSITION_X
                touch["x"] = value
            elif ev_type == 3 and code == 53 and touch:  # ABS_MT_POSITION_Y
                touch["y"] = value

        # 打印最后一次有效按下坐标（调试用）
        if touches:
            t = touches[-1]
            print(f"[touch] x={t.get('x')}, y={t.get('y')}, TAB_Y={TAB_Y}")
        else:
            print(f"[touch] no valid touch, raw_bytes={len(raw)}")

        # 取最后一次按下坐标，判断是否在 Tab 区域
        for ev in reversed(touches):
            x, y = ev.get("x", -1), ev.get("y", -1)
            print(f"[touch] checking x={x}, y={y}, TAB_Y={TAB_Y}, y>=TAB_Y: {y >= TAB_Y}")
            if y >= TAB_Y:
                    # 映射到 tab index
                    tab_idx = x // 200
                    tab_idx = max(0, min(3, tab_idx))
                    views = ["day", "week", "todo", "habit"]
                    return views[tab_idx]

        return current_view

    except Exception as e:
        try:
            subprocess.run([
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-i", KINDLE_KEY, f"root@{KINDLE_HOST}",
                "killall -CONT cvm"
            ], capture_output=True, timeout=5)
        except Exception:
            pass
        return current_view


def display_loop():
    """主循环：渲染 → 触摸读取 → 视图切换
    轮询间隔 60 秒（仅用于时钟更新），无触摸时不反复 STOP cvm
    """
    global current_view, display_loop_running
    _stop_event.clear()
    logging.info(f"[display] loop starting, view={current_view}")

    png = render_frame(current_view)
    logging.info(f"[display] initial full refresh, frame_size={len(png)}")
    try:
        push_frame_to_kindle(png)  # 启动时一次全屏 GC16
    except subprocess.CalledProcessError as e:
        logging.error(f"[display] initial push failed: {e}")
    logging.info("[display] initial push done")

    while display_loop_running:
        new_view = read_touch_from_kindle()  # STOP→读触摸→CONT
        with _state_lock:
            if new_view != current_view:
                current_view = new_view
                print(f"[display] switched to view: {current_view}")
                png = render_frame(current_view)
                try:
                    push_frame_to_kindle(png)  # 全屏 GC16
                except subprocess.CalledProcessError as e:
                    logging.error(f"[display] push failed: {e}")
            else:
                # 无视图切换，每 60 秒局部刷新时间（不 STOP cvm，保持时钟更新）
                logging.info(f"[display] no switch, waiting 60s, view={current_view}")
                _stop_event.wait(timeout=60)  # 可被 stop() 立即唤醒
                if not display_loop_running:
                    break
                logging.info(f"[display] waking, rendering frame...")
                png = render_frame(current_view)
                logging.info(f"[display] pushing partial frame, size={len(png)}")
                try:
                    push_frame_to_kindle_partial(png)  # 只 eips -g，不 STOP
                except subprocess.CalledProcessError as e:
                    logging.error(f"[display] partial push failed: {e}")
                logging.info(f"[display] partial push done")


@app.post("/start")
def start_calendar():
    global calendar_active, display_loop_running
    with _state_lock:
        if not display_loop_running:
            calendar_active = True
            display_loop_running = True
            _stop_event.clear()
            t = threading.Thread(target=display_loop, daemon=True)
            t.start()
    return {"status": "started", "active": calendar_active, "view": current_view}


@app.post("/stop")
def stop_calendar():
    global calendar_active, display_loop_running
    with _state_lock:
        calendar_active = False
        display_loop_running = False
    _stop_event.set()  # 立即唤醒 display_loop 的 wait()
    return {"status": "stopped", "active": calendar_active}


@app.post("/switch/{view_name}")
def switch_view(view_name: str):
    """切换视图并立即推送到 Kindle"""
    global current_view, display_loop_running
    valid = ["day", "week", "todo", "habit"]
    if view_name not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid view. Must be one of {valid}")
    with _state_lock:
        current_view = view_name
        view = current_view
    png = render_frame(view)
    push_frame_to_kindle(png)
    return {"status": "ok", "view": view}


@app.get("/frame")
def get_frame():
    """HTTP 抓帧接口（调试用，返回当前视图 PNG）"""
    with _state_lock:
        view = current_view
    return Response(content=render_frame(view), media_type="image/png")


@app.get("/frame/{view_name}")
def get_frame_view(view_name: str):
    """HTTP 抓帧接口（指定视图）"""
    valid = ["day", "week", "todo", "habit"]
    if view_name not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid view. Must be one of {valid}")
    return Response(content=render_frame(view_name), media_type="image/png")


@app.get("/debug/partial_push")
def debug_partial_push():
    """手动触发一次 partial push（调试用）"""
    with _state_lock:
        view = current_view
    png = render_frame(view)
    push_frame_to_kindle_partial(png)
    return {"status": "ok", "view": view, "size": len(png)}


# SPA 路由：所有非 API 路径返回 index.html
@app.get("/{path:path}")
async def spa_route(path: str):
    if path.startswith("api/") or path.startswith("habits/") or path in ("health", "events", "sync", "start", "stop", "switch", "frame"):
        raise HTTPException(404)
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    raise HTTPException(404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
