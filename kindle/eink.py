"""E-Ink Display Driver for Kindle Touch

This module provides a framebuffer interface for writing to the e-ink display.
Works with Kindle Touch (KNT) after jailbreak with KUAL installed.
"""

import struct
import os
from typing import Tuple

class EInkDisplay:
    """E-Ink framebuffer interface"""

    FB_PATH = "/dev/fb0"

    def __init__(self):
        self.width = 600
        self.height = 800
        self.fb = None
        self._init_framebuffer()

    def _init_framebuffer(self):
        """Initialize framebuffer"""
        if os.path.exists(self.FB_PATH):
            self.fb = open(self.FB_PATH, "wb")
            # Get actual screen size from fb_var_screeninfo
            self._update_geometry()

    def _update_geometry(self):
        """Read framebuffer geometry"""
        # For Kindle Touch, typical size is 600x800
        # In production, would read via ioctl
        pass

    def clear(self, color: int = 255):
        """Clear screen to white (255) or black (0)"""
        if self.fb:
            self.fb.seek(0)
            # Kindle uses 4-bit grayscale, so repeat color values
            self.fb.write(bytes([color] * (self.width * self.height)))

    def draw_rect(self, x: int, y: int, w: int, h: int, color: int = 0):
        """Draw filled rectangle"""
        if not self.fb:
            return

        for row in range(y, min(y + h, self.height)):
            self.fb.seek(row * self.width + x)
            self.fb.write(bytes([color] * w))

    def draw_text(self, x: int, y: int, text: str, size: int = 16, color: int = 0):
        """Draw text at position (simplified - uses built-in font)"""
        # In production, would use PIL or custom font renderer
        pass

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: int = 0):
        """Draw line using Bresenham's algorithm"""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            self._set_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def _set_pixel(self, x: int, y: int, color: int):
        """Set single pixel"""
        if 0 <= x < self.width and 0 <= y < self.height and self.fb:
            self.fb.seek(y * self.width + x)
            self.fb.write(bytes([color]))

    def update(self):
        """Full screen refresh - necessary for e-ink"""
        if self.fb:
            self.fb.flush()
            # Send e-ink refresh command via ioctl
            # This varies by device

    def partial_update(self, x: int, y: int, w: int, h: int):
        """Partial refresh for faster updates"""
        # For touched regions only
        pass

    def close(self):
        """Close framebuffer"""
        if self.fb:
            self.fb.close()
            self.fb = None

# Global display instance
_display = None

def get_display() -> EInkDisplay:
    """Get or create global display instance"""
    global _display
    if _display is None:
        _display = EInkDisplay()
    return _display