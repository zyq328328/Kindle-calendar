"""Simple Virtual Keyboard for Kindle Calendar"""

from typing import List, Tuple

class Keyboard:
    """Simple text input keyboard for e-ink display"""

    KEYBOARD_LAYOUT = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "⌫"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
        ["Z", "X", "C", "V", "B", "N", "M", "-"],
        ["空格", "确认"]
    ]

    def __init__(self, screen_width: int, screen_height: int, margin: int = 20):
        self.sw = screen_width
        self.sh = screen_height
        self.margin = margin
        self.key_width = (screen_width - margin * 2) // 10
        self.key_height = 40
        self.keys = self._build_key_rects()

    def _build_key_rects(self) -> List[Tuple]:
        """Build list of (x, y, w, h, char) tuples"""
        rects = []
        y = self.sh - 250

        for row in self.KEYBOARD_LAYOUT:
            x = self.margin
            for char in row:
                w = self.key_width
                if char == "空格":
                    w = self.key_width * 4
                elif char == "确认":
                    w = self.key_width * 2
                elif char in ["Z", "X", "C", "V", "B", "N", "M"]:
                    w = self.key_width * 1
                elif char in ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]:
                    w = self.key_width

                rects.append((x, y, w, self.key_height, char))
                x += w + 5

            y += self.key_height + 5

        return rects

    def handle_tap(self, x: int, y: int) -> str:
        """Handle tap, returns key char or action"""
        for rect in self.keys:
            rx, ry, rw, rh, char = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return char
        return ""

    def get_key_rect(self, char: str) -> Tuple:
        """Get rect for specific key"""
        for rect in self.keys:
            if rect[4] == char:
                return rect
        return None

def draw_keyboard(display, keyboard: Keyboard):
    """Draw keyboard to display"""
    for rect in keyboard.keys:
        x, y, w, h, char = rect
        # Draw key background
        display.draw_rect(x, y, w - 5, h, 220)  # light gray
        display.draw_rect(x, y, w - 5, h, 0)  # black border

        # Draw key label
        if char == "⌫":
            display.draw_text(x + 5, y + 12, "⌫", size=18, color=0)
        elif char == "确认":
            display.draw_text(x + 20, y + 12, "确认", size=16, color=0)
        elif char == "空格":
            display.draw_text(x + 60, y + 12, "空格", size=14, color=128)
        else:
            display.draw_text(x + 10, y + 10, char, size=18, color=0)

def simple_input(display, keyboard: Keyboard, prompt: str, initial: str = "") -> Tuple[str, bool]:
    """Simple text input with keyboard

    Returns (result_string, confirmed)
    """
    text = initial
    confirmed = False

    while not confirmed:
        # Draw input area
        display.clear(255)
        display.draw_rect(keyboard.margin, 100, display.width - 40, 50, 255)
        display.draw_rect(keyboard.margin, 100, display.width - 40, 50, 0)
        display.draw_text(keyboard.margin + 10, 115, prompt + ":", size=14, color=64)
        display.draw_text(keyboard.margin + 10, 140, text or "_", size=20, color=0)

        # Draw keyboard
        draw_keyboard(display, keyboard)

        display.update()

        # Wait for input
        action = read_input()
        if not action:
            continue

        if action.startswith("tap_"):
            _, x, y = action.split("_")
            x, y = int(x), int(y)
            key = keyboard.handle_tap(x, y)

            if key == "⌫":
                text = text[:-1]
            elif key == "确认":
                confirmed = True
            elif key == "空格":
                text += " "
            elif key:
                text += key.lower()

        elif action == "escape":
            return text, False

    return text, True

def read_input() -> str:
    """Read user input from /dev/input/event*"""
    import os
    import struct

    EVENT_DEV = "/dev/input/event0"
    if not os.path.exists(EVENT_DEV):
        return None

    try:
        with open(EVENT_DEV, "rb") as f:
            import select
            if select.select([f], [], [], 0.1)[0]:
                data = f.read(24)
                if len(data) < 24:
                    return None

                _, t_type, code, value = struct.unpack("llHHI", data)

                if t_type == 1 and code == 0x14a:  # BTN_TOUCH
                    if value == 1:
                        return "tap"
                    elif value == 0:
                        return "tap_up"
                elif t_type == 3:  # EV_ABS
                    if code == 0x03:
                        return f"tap_0_0"  # Will be updated with real coords
                    elif code == 0x04:
                        return "tap"
                elif t_type == 0:  # EV_SYN
                    return "tap"

    except Exception:
        pass

    return None