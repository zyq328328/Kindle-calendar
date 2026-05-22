#!/usr/bin/env python3
"""
Kindle 日历主程序 - 新版左侧导航布局
触摸坐标: 物理屏600x800 → 渲染图800x600
旋转映射: x_render = y_phys, y_render = 600 - x_phys
左侧导航栏触摸 x_render < 80
"""
import os, sys, datetime

BASE = "/mnt/us/extensions/KindleCalendar/bin"
sys.path.insert(0, BASE)

from touch_input import wait_for_touch
from calendar_renderer import render_frame, fetch_events
from eink_display import show_image_full

RW, RH = 800, 600
NAV_W = 80   # 左侧导航栏宽度

VIEWS = ["home", "day", "three_day", "list", "quadrant", "habit", "settings"]
current_view = "home"
current_date = datetime.date.today()
IMG_PATH = "/tmp/calendar_frame.png"


def rot_coord(x_phys, y_phys):
    """物理600x800 → 渲染800x600（顺时针90°）"""
    return y_phys, RW - x_phys


def render_current():
    date_str = current_date.isoformat()
    all_events = fetch_events()
    # 待办/习惯/清单视图需要全部事件
    if current_view in ("todo", "habit", "quadrant", "list", "home"):
        events = all_events
    else:
        events = [e for e in all_events if e.get("date", "").startswith(date_str)]
    render_frame(current_view, date_str, events, IMG_PATH)
    show_image_full(IMG_PATH)


def handle_touch(x_phys, y_phys):
    """返回操作字符串"""
    global current_view, current_date

    xr, yr = rot_coord(x_phys, y_phys)

    # 左侧导航栏（x_render < 80）
    if xr < NAV_W:
        # 导航项：首/日/三/周/清/四/习/设，每项高52px，起始y=10
        NAV_ITEMS = ["home", "day", "three_day", "list", "quadrant", "habit", "settings"]
        idx = (yr - 10) // 52
        idx = max(0, min(idx, len(NAV_ITEMS) - 1))
        new_view = NAV_ITEMS[idx]
        if new_view != current_view:
            current_view = new_view
            print(f"[app] Switched to view: {current_view}")
            render_current()
        return "switch_view"

    # 主内容区触摸 → 日期切换
    # 上半部分=前一天，下半部分=后一天
    if yr < RH // 2:
        current_date = current_date - datetime.timedelta(days=1)
        print(f"[app] prev: {current_date}")
    else:
        current_date = current_date + datetime.timedelta(days=1)
        print(f"[app] next: {current_date}")
    return "navigate_day"


def main():
    print(f"[app] Kindle Calendar started (nav layout)")
    print(f"[app] View: {current_view}, Date: {current_date}")

    render_current()
    print("[app] Touch enabled.")

    while True:
        touch = wait_for_touch(timeout_ms=60000)
        if touch is None:
            render_current()
            continue

        op = handle_touch(touch["x"], touch["y"])
        if op in ("switch_view", "navigate_day"):
            render_current()
        elif op == "quit":
            break


if __name__ == "__main__":
    main()
