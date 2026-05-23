"""UI Module for Kindle Calendar - Simplified Interaction

Handles touch-based interaction:
- Tap on checkbox: toggle completion
- Tap on date: switch to that date
- Swipe left/right: change views
"""

from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
from models import Event, EventStore
import config

MARGIN = 20
HEADER_HEIGHT = 60
DATE_HEADER_HEIGHT = 40
EVENT_ITEM_HEIGHT = 50

class Colors:
    BLACK = 0
    DARK_GRAY = 64
    MEDIUM_GRAY = 128
    LIGHT_GRAY = 192
    WHITE = 255

class UIView:
    """Base class for all views"""
    def __init__(self, display, event_store, sync_manager=None):
        self.display = display
        self.event_store = event_store
        self.sync_manager = sync_manager

    def render(self):
        raise NotImplementedError

    def handle_tap(self, x: int, y: int) -> bool:
        """Handle tap - returns True if handled"""
        return False

    def handle_swipe(self, direction: str) -> bool:
        """Handle swipe - returns True if handled"""
        return False

class HomeView(UIView):
    """Three-day calendar view"""

    def __init__(self, display, event_store, sync_manager=None):
        super().__init__(display, event_store, sync_manager)
        self.view_days = [date.today() + timedelta(days=i) for i in range(3)]
        self.selected_day_index = 0
        self.event_rects = []

    def render(self):
        d = self.display
        d.clear(Colors.WHITE)
        self._draw_header()
        self._draw_date_selector()
        self.event_rects = self._draw_events()
        self._draw_nav()
        d.update()

    def _draw_header(self):
        d = self.display
        now = datetime.now()
        d.draw_text(MARGIN, MARGIN + 10, "📅 智能台历", size=24, color=Colors.BLACK)
        d.draw_text(SCREEN_WIDTH - 100, MARGIN + 10, now.strftime("%H:%M"), size=28, color=Colors.BLACK)
        d.draw_line(MARGIN, HEADER_HEIGHT, SCREEN_WIDTH - MARGIN, HEADER_HEIGHT, Colors.LIGHT_GRAY)

    def _draw_date_selector(self):
        d = self.display
        y = HEADER_HEIGHT + 15

        for i, day in enumerate(self.view_days):
            is_selected = (i == self.selected_day_index)
            is_today = (day == date.today())
            box_x = MARGIN + i * 180
            box_width = 160

            if is_selected:
                d.draw_rect(box_x, y, box_width, DATE_HEADER_HEIGHT, Colors.LIGHT_GRAY)

            day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            day_name = day_names[day.weekday()]
            date_text = f"{day.month}/{day.day}"
            if is_today:
                date_text += " 今天"

            d.draw_text(box_x + 10, y + 10, f"{day_name} {date_text}", size=16,
                       color=Colors.BLACK if is_selected else Colors.MEDIUM_GRAY)

    def _draw_events(self) -> List[Tuple]:
        d = self.display
        rects = []
        selected_date = self.view_days[self.selected_day_index]
        events = self.event_store.get_by_date(selected_date.strftime("%Y-%m-%d"))

        y = HEADER_HEIGHT + DATE_HEADER_HEIGHT + 40

        if not events:
            d.draw_text(MARGIN, y + 50, "暂无日程", size=18, color=Colors.MEDIUM_GRAY)
            return rects

        for i, event in enumerate(events):
            item_y = y + i * EVENT_ITEM_HEIGHT
            rects.append((MARGIN, item_y, SCREEN_WIDTH - MARGIN * 2, EVENT_ITEM_HEIGHT, event))
            self._draw_event_item(event, item_y, i)

        return rects

    def _draw_event_item(self, event: Event, y: int, index: int):
        d = self.display
        priority_colors = {"urgent": Colors.BLACK, "important": Colors.MEDIUM_GRAY, "normal": Colors.LIGHT_GRAY}

        # Checkbox (tappable area)
        checkbox_x = MARGIN + 5
        checkbox_y = y + 12
        if event.completed:
            d.draw_rect(checkbox_x, checkbox_y, 22, 22, Colors.BLACK)
            d.draw_text(checkbox_x + 4, checkbox_y + 3, "✓", size=16, color=Colors.WHITE)
        else:
            d.draw_rect(checkbox_x, checkbox_y, 22, 22, Colors.WHITE)
            d.draw_rect(checkbox_x, checkbox_y, 22, 22, Colors.LIGHT_GRAY)

        # Event time
        time_text = event.time if event.time else "--:--"
        d.draw_text(MARGIN + 45, y + 10, time_text, size=14, color=Colors.DARK_GRAY)

        # Event title
        title_color = Colors.MEDIUM_GRAY if event.completed else Colors.BLACK
        d.draw_text(MARGIN + 110, y + 10, event.title[:18], size=16, color=title_color)

        # Priority dot
        indicator_color = priority_colors.get(event.priority, Colors.MEDIUM_GRAY)
        d.draw_rect(SCREEN_WIDTH - MARGIN - 25, y + 15, 10, 10, indicator_color)

        # Separator
        d.draw_line(MARGIN, y + EVENT_ITEM_HEIGHT - 2, SCREEN_WIDTH - MARGIN, y + EVENT_ITEM_HEIGHT - 2, Colors.LIGHT_GRAY)

    def _draw_nav(self):
        d = self.display
        y = SCREEN_HEIGHT - 50
        nav_items = ["← 日历", "待办", "倒数日", "象限 →"]
        for i, item in enumerate(nav_items):
            x = MARGIN + i * 130
            d.draw_text(x, y, item, size=14, color=Colors.MEDIUM_GRAY)

    def handle_tap(self, x: int, y: int) -> bool:
        # Check date selector
        date_y = HEADER_HEIGHT + 15
        if date_y <= y <= date_y + DATE_HEADER_HEIGHT:
            for i in range(3):
                box_x = MARGIN + i * 180
                if box_x <= x <= box_x + 160:
                    self.selected_day_index = i
                    return True

        # Check event checkboxes
        for rect in self.event_rects:
            rx, ry, rw, rh, event = rect
            if ry <= y <= ry + rh:
                # Toggle checkbox
                if rx + 5 <= x <= rx + 30:
                    event.completed = not event.completed
                    self.event_store.save()
                    if self.sync_manager:
                        self.sync_manager.push_event(event)
                    return True

        return False

class TodoView(UIView):
    """Todo list view"""

    def __init__(self, display, event_store, sync_manager=None):
        super().__init__(display, event_store, sync_manager)
        self.filter = "all"
        self.event_rects = []

    def render(self):
        d = self.display
        d.clear(Colors.WHITE)
        self._draw_header()
        self._draw_filter_tabs()
        self.event_rects = self._draw_todo_list()
        self._draw_nav()
        d.update()

    def _draw_header(self):
        d = self.display
        d.draw_text(MARGIN, MARGIN + 10, "✅ 待办清单", size=24, color=Colors.BLACK)
        d.draw_line(MARGIN, HEADER_HEIGHT, SCREEN_WIDTH - MARGIN, HEADER_HEIGHT, Colors.LIGHT_GRAY)

    def _draw_filter_tabs(self):
        d = self.display
        y = HEADER_HEIGHT + 15
        tabs = [("全部", "all"), ("待办", "pending"), ("已完成", "completed")]
        for i, (label, value) in enumerate(tabs):
            x = MARGIN + i * 100
            is_selected = (self.filter == value)
            if is_selected:
                d.draw_rect(x, y, 80, 30, Colors.LIGHT_GRAY)
            d.draw_text(x + 10, y + 8, label, size=14, color=Colors.BLACK if is_selected else Colors.MEDIUM_GRAY)

    def _draw_todo_list(self) -> List[Tuple]:
        d = self.display
        rects = []
        y = HEADER_HEIGHT + 60

        if self.filter == "all":
            events = self.event_store.get_pending()
        elif self.filter == "pending":
            events = [e for e in self.event_store.events if not e.completed and not e.is_countdown]
        else:
            events = [e for e in self.event_store.events if e.completed]

        if not events:
            d.draw_text(MARGIN, y + 50, "暂无待办", size=18, color=Colors.MEDIUM_GRAY)
            return rects

        for event in events:
            rects.append((MARGIN, y, SCREEN_WIDTH - MARGIN * 2, EVENT_ITEM_HEIGHT, event))
            self._draw_todo_item(event, y)
            y += EVENT_ITEM_HEIGHT

        return rects

    def _draw_todo_item(self, event: Event, y: int):
        d = self.display
        checkbox_x = MARGIN + 5

        if event.completed:
            d.draw_rect(checkbox_x, y + 5, 22, 22, Colors.BLACK)
            d.draw_text(checkbox_x + 4, y + 8, "✓", size=16, color=Colors.WHITE)
            title_color = Colors.MEDIUM_GRAY
        else:
            d.draw_rect(checkbox_x, y + 5, 22, 22, Colors.WHITE)
            d.draw_rect(checkbox_x, y + 5, 22, 22, Colors.LIGHT_GRAY)
            title_color = Colors.BLACK

        d.draw_text(checkbox_x + 35, y + 5, event.title[:22], size=16, color=title_color)
        d.draw_text(checkbox_x + 35, y + 25, f"{event.date} {event.time or ''}", size=12, color=Colors.MEDIUM_GRAY)
        d.draw_line(MARGIN, y + EVENT_ITEM_HEIGHT - 2, SCREEN_WIDTH - MARGIN, y + EVENT_ITEM_HEIGHT - 2, Colors.LIGHT_GRAY)

    def _draw_nav(self):
        d = self.display
        y = SCREEN_HEIGHT - 50
        nav_items = ["← 日历", "倒数日", "象限 →"]
        for i, item in enumerate(nav_items):
            x = MARGIN + 60 + i * 140
            d.draw_text(x, y, item, size=14, color=Colors.MEDIUM_GRAY)

    def handle_tap(self, x: int, y: int) -> bool:
        # Check filter tabs
        tab_y = HEADER_HEIGHT + 15
        if tab_y <= y <= tab_y + 30:
            for i in range(3):
                if MARGIN + i * 100 <= x <= MARGIN + i * 100 + 80:
                    self.filter = ["all", "pending", "completed"][i]
                    return True

        # Check event checkboxes
        for rect in self.event_rects:
            rx, ry, rw, rh, event = rect
            if ry <= y <= ry + rh:
                if rx + 5 <= x <= rx + 30:
                    event.completed = not event.completed
                    self.event_store.save()
                    if self.sync_manager:
                        self.sync_manager.push_event(event)
                    return True

        return False

    def handle_swipe(self, direction: str) -> bool:
        if direction == "left":
            self.filter = {"all": "pending", "pending": "completed", "completed": "all"}[self.filter]
            return True
        elif direction == "right":
            self.filter = {"all": "completed", "pending": "all", "completed": "pending"}[self.filter]
            return True
        return False

class CountdownView(UIView):
    """Countdown events view"""

    def render(self):
        d = self.display
        d.clear(Colors.WHITE)
        d.draw_text(MARGIN, MARGIN + 10, "⏰ 倒数日", size=24, color=Colors.BLACK)
        d.draw_line(MARGIN, HEADER_HEIGHT, SCREEN_WIDTH - MARGIN, HEADER_HEIGHT, Colors.LIGHT_GRAY)

        y = HEADER_HEIGHT + 30
        countdowns = self.event_store.get_countdowns()

        if not countdowns:
            d.draw_text(MARGIN, y + 50, "暂无倒数日", size=18, color=Colors.MEDIUM_GRAY)
        else:
            for event in countdowns:
                self._draw_countdown_item(event, y)
                y += EVENT_ITEM_HEIGHT + 20

        y = SCREEN_HEIGHT - 50
        nav_items = ["← 日历", "待办", "象限 →"]
        for i, item in enumerate(nav_items):
            x = MARGIN + 60 + i * 140
            d.draw_text(x, y, item, size=14, color=Colors.MEDIUM_GRAY)

        d.update()

    def _draw_countdown_item(self, event: Event, y: int):
        d = self.display
        days = event.days_until

        if days is not None:
            if days < 0:
                days_text = f"{-days}"
                days_color = Colors.DARK_GRAY
            elif days == 0:
                days_text = "今天!"
                days_color = Colors.BLACK
            else:
                days_text = f"{days}"
                days_color = Colors.BLACK
        else:
            days_text = "?"
            days_color = Colors.MEDIUM_GRAY

        d.draw_text(MARGIN, y, days_text, size=48, color=days_color)
        d.draw_text(MARGIN + 80, y + 15, "天", size=18, color=Colors.MEDIUM_GRAY)
        d.draw_text(MARGIN + 120, y + 15, event.title[:20], size=18, color=Colors.BLACK)

        if event.countdown_target:
            d.draw_text(MARGIN + 120, y + 35, f"目标: {event.countdown_target}", size=12, color=Colors.MEDIUM_GRAY)

class QuadrantView(UIView):
    """Eisenhower Matrix - Four Quadrant View"""

    def render(self):
        d = self.display
        d.clear(Colors.WHITE)
        d.draw_text(MARGIN, MARGIN + 10, "📊 四象限看板", size=24, color=Colors.BLACK)
        d.draw_text(SCREEN_WIDTH - 100, MARGIN + 10, datetime.now().strftime("%m/%d"), size=16, color=Colors.MEDIUM_GRAY)
        d.draw_line(MARGIN, HEADER_HEIGHT, SCREEN_WIDTH - MARGIN, HEADER_HEIGHT, Colors.LIGHT_GRAY)

        quad_w = (SCREEN_WIDTH - MARGIN * 3) // 2
        quad_h = (SCREEN_HEIGHT - HEADER_HEIGHT - 80) // 2

        self._draw_quadrant(0, HEADER_HEIGHT + 15, quad_w, quad_h, "🔴 紧急重要", "urgent", Colors.BLACK)
        self._draw_quadrant(quad_w + MARGIN, HEADER_HEIGHT + 15, quad_w, quad_h, "🟡 重要不紧急", "important", Colors.MEDIUM_GRAY)
        self._draw_quadrant(0, HEADER_HEIGHT + 15 + quad_h + 10, quad_w, quad_h, "🟠 紧急不重要", "delegated", Colors.DARK_GRAY)
        self._draw_quadrant(quad_w + MARGIN, HEADER_HEIGHT + 15 + quad_h + 10, quad_w, quad_h, "⚪ 不紧急不重要", "eliminate", Colors.LIGHT_GRAY)

        y = SCREEN_HEIGHT - 50
        nav_items = ["← 日历", "待办", "倒数日 →"]
        for i, item in enumerate(nav_items):
            x = MARGIN + 60 + i * 140
            d.draw_text(x, y, item, size=14, color=Colors.MEDIUM_GRAY)

        d.update()

    def _draw_quadrant(self, x: int, y: int, w: int, h: int, title: str, priority: str, border_color: int):
        d = self.display
        d.draw_rect(x, y, w, h, Colors.WHITE)
        d.draw_rect(x, y, w, h, border_color)
        d.draw_text(x + 10, y + 8, title, size=14, color=border_color)
        d.draw_line(x + 5, y + 28, x + w - 5, y + 28, Colors.LIGHT_GRAY)

        events = self._get_quadrant_events(priority)
        item_y = y + 38

        if not events:
            d.draw_text(x + 10, item_y, "(空)", size=12, color=Colors.LIGHT_GRAY)
            return

        for event in events[:4]:
            d.draw_rect(x + 10, item_y + 4, 8, 8, border_color)
            d.draw_text(x + 24, item_y, event.title[:12], size=12, color=Colors.BLACK)
            item_y += 25

    def _get_quadrant_events(self, priority: str) -> list:
        events = [e for e in self.event_store.events if not e.completed and not e.is_countdown]

        if priority == "urgent":
            return [e for e in events if e.priority == "urgent" or e.is_past]
        elif priority == "important":
            return [e for e in events if e.priority == "important" and not e.is_past]
        elif priority == "delegated":
            return [e for e in events if e.priority == "normal" and not e.is_past]
        else:
            return [e for e in events if e.completed]

class UIManager:
    """Main UI controller managing views and navigation"""

    def __init__(self, display, event_store, sync_manager=None):
        self.display = display
        self.event_store = event_store
        self.sync_manager = sync_manager
        self.views = {
            "home": HomeView(display, event_store, sync_manager),
            "todo": TodoView(display, event_store, sync_manager),
            "countdown": CountdownView(display, event_store, sync_manager),
            "quadrant": QuadrantView(display, event_store, sync_manager),
        }
        self.current_view = "home"
        self.view_order = ["home", "todo", "countdown", "quadrant"]

    def render(self):
        view = self.views[self.current_view]
        view.render()

    def handle_input(self, action: str, x: int = None, y: int = None):
        if action == "swipe_left":
            self.navigate("left")
        elif action == "swipe_right":
            self.navigate("right")
        elif action == "tap" and x and y:
            view = self.views[self.current_view]
            if not view.handle_tap(x, y):
                pass  # Tap not handled
        elif action.startswith("tap_"):
            # Parse tap coordinates
            try:
                _, x_str, y_str = action.split("_")
                x, y = int(x_str), int(y_str)
                view = self.views[self.current_view]
                view.handle_tap(x, y)
            except:
                pass

    def navigate(self, direction: str):
        current_index = self.view_order.index(self.current_view)
        if direction == "left":
            self.current_view = self.view_order[(current_index - 1) % len(self.view_order)]
        elif direction == "right":
            self.current_view = self.view_order[(current_index + 1) % len(self.view_order)]

SCREEN_WIDTH = config.SCREEN_WIDTH
SCREEN_HEIGHT = config.SCREEN_HEIGHT