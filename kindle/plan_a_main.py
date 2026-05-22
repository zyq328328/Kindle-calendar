#!/usr/bin/env python3
"""
Kindle 日历主程序 - 新版左侧导航布局
触摸坐标: 物理屏600x800 → 渲染图800x600
旋转映射: x_render = y_phys, y_render = 600 - x_phys
左侧导航栏触摸 x_render < 80

方案A当前状态：TODO - 等待 touch_input.py 和 eink_display.py 实现
"""
import os, sys, datetime

BASE = "/mnt/us/extensions/KindleCalendar/bin"
sys.path.insert(0, BASE)

# TODO: 实现以下模块后取消注释
# from touch_input import wait_for_touch
# from calendar_renderer import render_frame, fetch_events
# from eink_display import show_image_full

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
    """渲染当前视图并推送到屏幕 — 方案A待实现"""
    raise NotImplementedError("方案A: 等待 touch_input.py 和 eink_display.py 实现")


def handle_touch(x_phys, y_phys):
    """处理触摸 — 方案A待实现"""
    raise NotImplementedError("方案A: 等待 touch_input.py 和 eink_display.py 实现")


def main():
    """主循环 — 方案A待实现"""
    raise NotImplementedError("方案A: 等待 touch_input.py 和 eink_display.py 实现")


if __name__ == "__main__":
    main()
