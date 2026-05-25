#!/usr/bin/env python3
"""
Kindle 日历主程序 - 三栏布局
触摸坐标: 物理屏600x800 → 渲染图800x600
旋转映射: x_render = 800 - y_phys, y_render = x_phys
右侧导航栏触摸 x_render > 740 (W - RIGHT_W = 800 - 60)
"""
import os
import sys
import datetime
import time
import subprocess
import threading
import urllib.request
import urllib.parse
import json
from PIL import Image, ImageDraw

BASE = "/mnt/us/extensions/KindleCalendar/bin"
sys.path.insert(0, BASE)
from touch_input import wait_for_touch
from calendar_renderer import render_frame, fetch_events, touch_to_view, W, H, RIGHT_W, LEFT_W, flatten_tree, _event_matches_date, _is_event_completed, render_confirm_view, render_calibration_view
from eink_display import show_image_full, show_image_partial

SERVER_URL = "http://192.168.10.7:8082/api/events"

current_view = "home"
current_date = datetime.date.today()
IMG_PATH = "/tmp/calendar_frame.png"
auto_refresh_enabled = False
auto_refresh_thread = None

# 确认页面状态（用于取消完成的确认）
# None 或 {"event_id": int, "event_type": str, "date": str, "event_title": str}
confirm_state = None

# 触屏校准状态
# None 或 {"phase": int, "points": [(x_phys, y_phys), ...], "dot_positions": [(x_rot, y_rot), ...]}
calibration_state = None


def restore_kindle():
    """恢复 Kindle 系统功能"""
    print("[quit] Restoring Kindle system...")
    try:
        # 恢复 volumd
        subprocess.run(["killall", "-CONT", "volumd"], stderr=subprocess.DEVNULL)
        # 恢复 awesome
        subprocess.run(["killall", "-CONT", "awesome"], stderr=subprocess.DEVNULL)
        # 恢复 pillow
        subprocess.run(
            ["lipc-set-prop", "com.lab126.pillow", "disableEnablePillow", "enable"],
            stderr=subprocess.DEVNULL
        )
        print("[quit] Kindle system restored")
    except Exception as e:
        print(f"[quit] Error: {e}")


def rot_coord(x_phys, y_phys):
    """
    物理600x800 → 渲染800x600
    逆时针90°旋转：x_render = 800 - y_phys, y_render = x_phys
    加入校准偏移修正
    """
    offset_x = 3   # X偏移修正
    offset_y = -22  # Y偏移修正
    return 800 - y_phys + offset_x, x_phys + offset_y


def mark_habit_completed(event_id, date):
    """调用习惯打卡API，只标记当天完成"""
    try:
        url = f"{SERVER_URL.replace('/api/events', '/api/habits')}/{event_id}/checkin?date={date}"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[api] Habit {event_id} checked in for {date}")
            return True
    except Exception as e:
        print(f"[api] Error checking in habit {event_id}: {e}")
        return False


def mark_todo_completed(event_id):
    """调用API标记待办完成"""
    try:
        url = f"{SERVER_URL}/{event_id}"
        data = json.dumps({"completed": True}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[api] Marked todo {event_id} as completed")
            return True
    except Exception as e:
        print(f"[api] Error marking todo {event_id} completed: {e}")
        return False


def uncheck_habit(event_id, date):
    """调用API取消习惯打卡"""
    try:
        url = f"{SERVER_URL.replace('/api/events', '/api/habits')}/{event_id}/uncheck?date={date}"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[api] Habit {event_id} unchecked for {date}")
            return True
    except Exception as e:
        print(f"[api] Error unchecking habit {event_id}: {e}")
        return False


def uncheck_todo(event_id):
    """调用API取消待办完成"""
    try:
        url = f"{SERVER_URL}/{event_id}"
        data = json.dumps({"completed": False}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="PUT",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[api] Marked todo {event_id} as uncompleted")
            return True
    except Exception as e:
        print(f"[api] Error unchecking todo {event_id}: {e}")
        return False


def find_tapped_todo(x_rot, y_rot, events):
    """
    在今日视图中查找被点击的待办项
    只有不含子项的待办可点击（无论是否为父项）
    """
    content_x = LEFT_W
    print(f"[find_todo] Looking for tap at ({x_rot}, {y_rot}), content_x={content_x}, W={W}, RIGHT_W={RIGHT_W}")
    
    # 只处理内容区（右侧导航栏除外）
    if x_rot >= W - RIGHT_W:
        print(f"[find_todo] Tap in navigation area, skipping")
        return None
    
    # 获取今日日期
    today_str = datetime.date.today().isoformat()
    print(f"[find_todo] Today: {today_str}")
    
    # 展开树结构并过滤今日的待办项和日程项
    flat_events = flatten_tree(events)
    print(f"[find_todo] Total events in tree: {len(flat_events)}")
    
    # 打印所有事件的信息（调试）
    for ev, depth in flat_events:
        ev_type = ev.get("type", "unknown")
        ev_date = ev.get("date", "N/A")
        ev_title = ev.get("title", "Untitled")[:20]
        matches = _event_matches_date(ev, today_str)
        ev_completed = ev.get("completed", False)
        print(f"[find_todo]   Event: type={ev_type}, title='{ev_title}', date='{ev_date}', matches={matches}, completed={ev_completed}")
    
    # 过滤今日的日程项（计算日程占用空间）
    schedules = [(ev, depth) for ev, depth in flat_events 
                 if ev.get("type") == "schedule" and _event_matches_date(ev, today_str)]
    num_schedules = min(len(schedules), 5)  # 最多显示5个
    print(f"[find_todo] Found {num_schedules} schedules for today")
    
    # 过滤今日的待办项
    todos = [(ev, depth) for ev, depth in flat_events 
             if ev.get("type") in ("todo", "habit") and _event_matches_date(ev, today_str)]
    
    print(f"[find_todo] Found {len(todos)} todos for today")
    for ev, depth in todos:
        print(f"[find_todo]   Todo: '{ev.get('title')}', date: '{ev.get('date')}', has_children: {bool(ev.get('children'))}")
    
    # 精确计算待办区域的起始位置（与渲染逻辑完全一致）
    # y=20(标题起始) + 45(标题高度) + 30(日程标题) + 日程内容 + 10(间隔) + 30(待办标题)
    y = 20 + 45 + 30 + num_schedules * 25 + 10 + 30
    
    print(f"[find_todo] Starting y position: {y}")
    
    for ev, depth in todos:
        indent = depth * 20
        # □ 的位置（content_x + 30 + indent, y）
        box_x = content_x + 30 + indent
        box_y = y
        
        title = ev.get("title", "Untitled")
        has_children = ev.get("children") and len(ev["children"]) > 0
        
        print(f"[find_todo] Todo: '{title}' at ({box_x}, {box_y}), depth={depth}, has_children={has_children}")
        
        # 检测范围：整个待办项行（从复选框到行尾）
        row_start_x = content_x + 20 + indent
        row_end_x = W - RIGHT_W - 10
        row_start_y = y - 5
        row_end_y = y + 25
        
        print(f"[find_todo]   Touch range: x=[{row_start_x},{row_end_x}], y=[{row_start_y},{row_end_y}]")
        
        # 检查触摸是否在待办项行内
        if (row_start_x <= x_rot <= row_end_x) and (row_start_y <= y_rot <= row_end_y):
            print(f"[find_todo]   TAPPED!")
            # 检查是否为有子项的父项（有子项的父项不可点击）
            if has_children:
                print(f"[find_todo]   But has children, skipping")
            else:
                print(f"[find_todo]   Returning this todo")
                return ev
        
        y += 25  # 每项高度
    
    print(f"[find_todo] No todo found at this position")
    return None


def handle_touch(x_phys, y_phys):
    """处理触摸"""
    global current_view, current_date, confirm_state, calibration_state

    # 转换坐标到渲染坐标系
    x_rot, y_rot = rot_coord(x_phys, y_phys)
    print(f"[touch] phys: ({x_phys}, {y_phys}) -> rot: ({x_rot}, {y_rot})")

    # 处理触屏校准
    if current_view == "calibration" or calibration_state is not None:
        state = calibration_state
        if state is not None:
            phase = state["phase"]
            dot_x, dot_y = state["dot_positions"][phase]
            print(f"[calib] phase={phase}, dot=({dot_x},{dot_y}), touch=({x_rot},{y_rot})")
            # 检测点击是否在圆点范围内（半径50像素）
            if abs(x_rot - dot_x) <= 50 and abs(y_rot - dot_y) <= 50:
                print(f"[calib] Point {phase + 1} tapped!")
                # 记录物理坐标
                state["points"].append((x_phys, y_phys))
                phase += 1
                if phase >= len(state["dot_positions"]):
                    # 校准完成，显示结果
                    print(f"[calib] Calibration done!")
                    print(f"[calib] Points (phys): {state['points']}")
                    calibration_state = None
                    current_view = "calibration_result"
                    render_current()
                else:
                    # 下一轮
                    state["phase"] = phase
                    calibration_state = state
                    render_current()
            else:
                print(f"[calib] Missed, try again")
        return False

    # 处理确认页面
    if current_view == "confirm" or confirm_state is not None:
        # 确认页面按钮检测（与 render_confirm_view 一致）
        # render_confirm_view: y=80 → +50=130 → +60=190, btn_y=190+40=230
        btn_h = 50
        btn_w = 140
        total_w = W
        gap = 40

        cancel_x = (total_w - 2 * btn_w - gap) // 2
        confirm_x = cancel_x + btn_w + gap
        btn_y = 230

        if cancel_x <= x_rot <= cancel_x + btn_w and btn_y <= y_rot <= btn_y + btn_h:
            # 取消
            print(f"[touch] Cancel in confirm page, returning to home")
            confirm_state = None
            current_view = "home"
            render_current()
            return False
        if confirm_x <= x_rot <= confirm_x + btn_w and btn_y <= y_rot <= btn_y + btn_h:
            # 确认取消
            print(f"[touch] Confirm in confirm page, unchecking")
            ev_type = confirm_state.get("event_type")
            event_id = confirm_state.get("event_id")
            date_str = confirm_state.get("date")
            confirm_state = None
            if ev_type == "habit":
                uncheck_habit(event_id, date_str)
            else:
                uncheck_todo(event_id)
            current_view = "home"
            render_current()
            return False
        # 点击按钮区域外 → 取消并返回
        print(f"[touch] Click outside buttons, dismissing confirm page")
        confirm_state = None
        current_view = "home"
        render_current()
        return False

    # 检查右侧导航栏
    if x_rot >= W - RIGHT_W:
        view = touch_to_view(x_rot, y_rot)
        print(f"[touch] view selected: {view}, current_view: {current_view}")
        if view:
            if view == "refresh":
                # 刷新当前视图
                render_current()
                return False
            if current_view != view:
                current_view = view
                print(f"[touch] view changed to: {current_view}")
                return True
        return False
    
    # 今日视图的待办项点击处理
    if current_view == "home":
        print(f"[touch] Current view is home, checking todo click")
        print(f"[touch] Touch position in content area: ({x_rot}, {y_rot})")
        # 转换为树结构（fetch_events返回flat格式，需要获取原始树）
        try:
            TREE_URL = SERVER_URL.replace("/api/events", "/api/events/tree")
            print(f"[touch] Fetching tree from: {TREE_URL}")
            req = urllib.request.Request(TREE_URL)
            with urllib.request.urlopen(req, timeout=3) as resp:
                print(f"[touch] HTTP response code: {resp.getcode()}")
                tree = json.loads(resp.read().decode())
                print(f"[touch] Got tree with {len(tree)} root events")
                # 打印所有事件信息用于调试
                for i, ev in enumerate(tree):
                    print(f"[touch] Event {i}: title='{ev.get('title')}', type='{ev.get('type')}', date='{ev.get('date')}'")
                    children = ev.get('children', [])
                    for j, child in enumerate(children):
                        print(f"[touch]   Child {j}: title='{child.get('title')}', type='{child.get('type')}', date='{child.get('date')}'")
                tapped_todo = find_tapped_todo(x_rot, y_rot, tree)
                if tapped_todo:
                    print(f"[touch] Tapped todo: {tapped_todo.get('title')}, type={tapped_todo.get('type')}, id={tapped_todo.get('id')}")
                    today_str = datetime.date.today().isoformat()
                    ev_type = tapped_todo.get("type")
                    event_id = tapped_todo["id"]

                    # 检查完成状态（用渲染时的逻辑：直接用 ev.get("completed")）
                    completed = tapped_todo.get("completed", False)
                    print(f"[touch] completed={completed}, ev_type={ev_type}")

                    if completed:
                        # 已完成：直接渲染确认页面
                        print(f"[touch] Event completed, rendering confirm page")
                        from PIL import Image as Img
                        img = Img.new('L', (W, H), 255)
                        draw = ImageDraw.Draw(img)
                        # 渲染确认页面
                        render_confirm_view(draw, [], 0, event_title=tapped_todo.get("title", "未知"))
                        # 保存并推送
                        img.save("/tmp/calendar_confirm.png")
                        show_image_full("/tmp/calendar_confirm.png")
                        # 切换到确认视图
                        current_view = "confirm"
                        confirm_state = {
                            "event_id": event_id,
                            "event_type": ev_type,
                            "date": today_str,
                            "event_title": tapped_todo.get("title", "未知"),
                        }
                        return False
                    else:
                        # 未完成：标记为完成
                        if ev_type == "habit":
                            success = mark_habit_completed(event_id, today_str)
                        else:
                            success = mark_todo_completed(event_id)
                        if success:
                            print(f"[touch] Marked as completed, re-rendering")
                            render_current()
                        else:
                            print(f"[touch] Failed to mark as completed")
                    return False
                else:
                    print(f"[touch] No todo tapped at this position")
        except Exception as e:
            print(f"[touch] Error fetching tree or finding todo: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"[touch] Current view is {current_view}, not home, skipping todo click")

    # 设置视图中的退出按钮处理
    if current_view == "settings":
        content_x = 0  # 设置视图占满左侧
        # 退出日历按钮
        if content_x + 50 <= x_rot <= content_x + 50 + 200 and 50 <= y_rot <= 85:
            restore_kindle()
            print("[quit] Exiting calendar...")
            sys.exit(0)
        # 触屏校准按钮
        if content_x + 50 <= x_rot <= content_x + 50 + 200 and 100 <= y_rot <= 135:
            print("[calib] Starting calibration")
            dot_positions = [(100, 100), (700, 100), (400, 300), (100, 500), (700, 500)]
            calibration_state = {
                "phase": 0,
                "points": [],
                "dot_positions": dot_positions,
            }
            current_view = "calibration"
            render_current()
            return False
        return False

    # 主内容区触摸 - 日视图和三日视图支持左右滑动切换日期
    if current_view == "day" or current_view == "three_day":
        # 左侧1/3区域 → 上一天
        if x_rot < W // 3:
            current_date -= datetime.timedelta(days=1)
            return True
        # 右侧1/3区域 → 下一天
        elif x_rot > W * 2 // 3:
            current_date += datetime.timedelta(days=1)
            return True

    return False


def render_current(full=True):
    """渲染当前视图并推送到屏幕"""
    print(f"[render] rendering view: {current_view}, date: {current_date}, full={full}")
    try:
        if current_view == "calibration" and calibration_state is not None:
            # 校准视图：直接渲染，不需要fetch
            img = Image.new('L', (W, H), 255)
            draw = ImageDraw.Draw(img)
            render_calibration_view(draw, calibration_state["phase"], calibration_state["dot_positions"])
            img.save(IMG_PATH)
            show_image_full(IMG_PATH)
        else:
            events = fetch_events()
            render_frame(current_view, current_date.isoformat(), events, IMG_PATH)
            if full:
                show_image_full(IMG_PATH)
            else:
                show_image_partial(IMG_PATH)
        print(f"[render] success")
    except Exception as e:
        print(f"[render] Error: {e}")
        # 即使出错也尝试渲染一个空的视图
        try:
            render_frame(current_view, current_date.isoformat(), [], IMG_PATH)
            show_image_full(IMG_PATH)
        except Exception as e2:
            print(f"[render] fallback failed: {e2}")


def clock_refresh_loop():
    """后台线程：每分钟刷新时钟区域（今日视图局部刷新）"""
    global auto_refresh_enabled
    while auto_refresh_enabled:
        time.sleep(60)  # 等待60秒
        if auto_refresh_enabled and current_view == "home":
            print("[clock_refresh] refreshing clock on home view")
            try:
                # 只刷新时钟区域（左侧面板），不触发全屏刷新
                render_current(full=False)
            except Exception as e:
                print(f"[clock_refresh] error: {e}")


def main():
    """主循环"""
    global auto_refresh_enabled, auto_refresh_thread
    print("[plan_a] Starting Kindle Calendar (三栏布局)")

    # 初始渲染
    render_current()

    # 启动自动刷新线程（今日视图每分钟局部刷新时钟）
    auto_refresh_enabled = True
    auto_refresh_thread = threading.Thread(target=clock_refresh_loop, daemon=True)
    auto_refresh_thread.start()
    print("[plan_a] auto clock refresh thread started")

    # 触摸主循环
    while True:
        coord = wait_for_touch()
        if coord:
            x_phys, y_phys = coord
            print(f"[touch] raw: ({x_phys}, {y_phys})")
            if handle_touch(x_phys, y_phys):
                print(f"[view] switched to {current_view}")
                render_current()


if __name__ == "__main__":
    main()