#!/usr/bin/env python3
"""
Kindle 日历主程序 - 新版左侧导航布局
触摸坐标: 物理屏600x800 → 渲染图800x600
旋转映射: x_render = 800 - y_phys, y_render = x_phys
左侧导航栏触摸 x_render < 80 → 物理 y_phys > 720
"""
import os
import sys
import datetime
import time

BASE = "/mnt/us/extensions/KindleCalendar/bin"
sys.path.insert(0, BASE)

from touch_input import wait_for_touch
from calendar_renderer import render_frame, fetch_events
from eink_display import show_image_full

RW, RH = 800, 600
NAV_W = 80   # 左侧导航栏宽度

VIEWS = ["home", "day", "three_day", "week", "list", "quadrant", "habit", "settings"]
current_view = "home"
current_date = datetime.date.today()
IMG_PATH = "/tmp/calendar_frame.png"

# 导航栏触摸区域 (render 坐标 800x600 横屏)
# 必须与 calendar_renderer.py 中的 NAV_ITEMS 一致
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

# 导航栏绘制参数 (与 calendar_renderer.py 一致)
NAV_ITEM_H = 52
NAV_START_Y = 10


def rot_coord(x_phys, y_phys):
    """
    物理600x800 → 渲染800x600
    逆时针90°旋转：x_render = 800 - y_phys, y_render = x_phys
    """
    return 800 - y_phys, x_phys


def handle_touch(x_phys, y_phys):
    """处理触摸"""
    global current_view, current_date

    # 转换坐标到渲染坐标系
    x_rot, y_rot = rot_coord(x_phys, y_phys)

    # 检查左侧导航栏 (x_render < 80)
    if x_rot < NAV_W:
        # 导航栏 y 范围从 NAV_START_Y=10 开始，每项高度 NAV_ITEM_H=52
        if y_rot < NAV_START_Y:
            return False  # 在标题区域，不响应

        # 计算触摸落在哪个导航项
        idx = int((y_rot - NAV_START_Y) // NAV_ITEM_H)
        if 0 <= idx < len(NAV_ITEMS):
            label, view = NAV_ITEMS[idx]
            if current_view != view:
                current_view = view
                print(f"[view] switched to {view}")
                return True
        return False

    # 主内容区触摸
    if current_view == "day" or current_view == "three_day":
        # 左右滑动切换日期
        if x_rot < RW // 3:
            current_date -= datetime.timedelta(days=1)
            return True
        elif x_rot > RW * 2 // 3:
            current_date += datetime.timedelta(days=1)
            return True

    return False


def render_current():
    """渲染当前视图并推送到屏幕"""
    try:
        events = fetch_events()
        render_frame(current_view, current_date.isoformat(), events, IMG_PATH)
        show_image_full(IMG_PATH)
    except Exception as e:
        print(f"[render] Error: {e}")


def main():
    """主循环"""
    print("[plan_a] Starting Kindle Calendar (Plan A)")

    # 初始渲染
    render_current()

    # 触摸主循环 - 不再定期刷新，只在有触摸时刷新
    while True:
        coord = wait_for_touch()
        if coord:
            x_phys, y_phys = coord
            print(f"[touch] raw: ({x_phys}, {y_phys})")
            if handle_touch(x_phys, y_phys):
                render_current()
        # 超时不做任何操作，保持屏幕现状


if __name__ == "__main__":
    main()
