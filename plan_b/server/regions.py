"""
600x800 触摸区域映射 (Kindle 7屏幕)
导航栏: y >= 700
主内容区: y < 700
"""
from datetime import date, timedelta
from typing import Literal

W, H = 600, 800
NAV_Y = 700  # 导航栏起始y

# 导航栏按钮分区 (y >= 700)
NAV_BUTTONS = [
    (0, 150, "day", "日"),
    (150, 300, "three_day", "三日"),
    (300, 450, "todo", "待办"),
    (450, 600, "habit", "习惯"),
]

# 主内容区滑动手势 (y < 700)
SWIPE_LEFT_X = 200   # x < 200: 左滑 prev_day
SWIPE_RIGHT_X = 400  # x > 400: 右滑 next_day
TAP_CENTER_X_MIN = 200
TAP_CENTER_X_MAX = 400

# 当前视图状态
_current_view: Literal["day", "three_day", "todo", "habit"] = "day"
_current_date: date = date.today()

def get_current_view() -> str:
    return _current_view

def get_current_date() -> str:
    return _current_date.isoformat()

def set_view(view: str) -> None:
    global _current_view
    _current_view = view

def set_date(d: date) -> None:
    global _current_date
    _current_date = d

def route_touch(x: int, y: int, action: str) -> tuple[str, str | None]:
    """
    触摸路由主逻辑
    返回 (action, view_name)
    action: next_day | prev_day | switch_view | quit | none | select_date
    view_name: 当 action=switch_view 时返回目标视图名
    """
    global _current_date

    # 导航栏区域
    if y >= NAV_Y:
        for x_min, x_max, view_name, label in NAV_BUTTONS:
            if x_min <= x < x_max:
                _current_view = view_name
                return ("switch_view", view_name)
        return ("none", None)

    # 主内容区
    if action == "tap":
        if x < SWIPE_LEFT_X:
            # 左滑 - 切换到前一天
            _current_date = _current_date - timedelta(days=1)
            return ("prev_day", None)
        elif x > SWIPE_RIGHT_X:
            # 右滑 - 切换到下一天
            _current_date = _current_date + timedelta(days=1)
            return ("next_day", None)
        else:
            # 中间区域 - 选中当前日期
            return ("select_date", None)

    # action=release 或其他
    return ("none", None)
