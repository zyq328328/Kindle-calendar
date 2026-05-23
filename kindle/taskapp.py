#!/usr/bin/env python3
import os
import sys
import time
import struct
import select
import socket
import json

SCREEN_W = 600
SCREEN_H = 800
SCREEN_STRIDE = 608
WHITE = 255
BLACK = 0
GRAY = 128
LIGHT_GRAY = 192

EV_KEY = 0x01
EV_ABS = 0x03
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36
ABS_MT_TRACKING_ID = 0x39
BTN_TOUCH = 0x14a

SERVER_URL = "http://192.168.10.7:8082"

def log(msg):
    with open('/tmp/app.log', 'a') as f:
        f.write(msg + '\n')

class Framebuffer:
    def __init__(self):
        log('FB: opening /dev/fb0')
        self.fd = os.open("/dev/fb0", os.O_RDWR)
        log('FB: opened')

    def clear(self, color=WHITE):
        log('FB.clear: start')
        for row in range(SCREEN_H):
            os.lseek(self.fd, row * SCREEN_STRIDE, os.SEEK_SET)
            os.write(self.fd, bytes([color]) * SCREEN_W)
        log('FB.clear: done')

    def fill_rect(self, x, y, w, h, color):
        for row in range(y, min(y+h, SCREEN_H)):
            os.lseek(self.fd, row * SCREEN_STRIDE + x, os.SEEK_SET)
            os.write(self.fd, bytes([color] * w))

    def draw_text(self, x, y, text, size=16, color=BLACK):
        log(f'FB.draw_text: x={x}, y={y}, text={text}')
        font = {
            'A': [0x18,0x24,0x42,0x7E,0x42,0x42,0x00],
            'B': [0x7C,0x42,0x42,0x7C,0x42,0x42,0x00],
            'C': [0x3C,0x42,0x80,0x80,0x42,0x3C,0x00],
            'D': [0x7C,0x42,0x42,0x42,0x42,0x7C,0x00],
            'E': [0x7E,0x40,0x40,0x7C,0x40,0x40,0x7E,0x00],
            '1': [0x08,0x18,0x38,0x18,0x18,0x18,0x7E,0x00],
            '2': [0x3C,0x42,0x02,0x0C,0x10,0x20,0x7E,0x00],
            '3': [0x3C,0x42,0x02,0x1C,0x02,0x42,0x3C,0x00],
            '4': [0x08,0x18,0x28,0x48,0x7E,0x08,0x08,0x00],
            '5': [0x7E,0x40,0x40,0x7C,0x02,0x42,0x3C,0x00],
            '6': [0x3C,0x42,0x40,0x7C,0x42,0x42,0x3C,0x00],
            '7': [0x7E,0x02,0x04,0x08,0x10,0x10,0x10,0x00],
            '8': [0x3C,0x42,0x42,0x3C,0x42,0x42,0x3C,0x00],
            '9': [0x3C,0x42,0x42,0x3E,0x02,0x04,0x38,0x00],
            '0': [0x3C,0x42,0x42,0x42,0x42,0x42,0x3C,0x00],
            'T': [0x7E,0x10,0x10,0x10,0x10,0x10,0x10,0x00],
            'a': [0x00,0x00,0x3C,0x42,0x42,0x42,0x3C,0x00],
            's': [0x00,0x3C,0x40,0x3C,0x02,0x42,0x3C,0x00],
            'k': [0x42,0x44,0x48,0x70,0x48,0x44,0x42,0x00],
            'L': [0x40,0x40,0x40,0x40,0x40,0x40,0x7E,0x00],
            'C': [0x3C,0x42,0x80,0x80,0x42,0x3C,0x00],
            '日': [0x00,0x7E,0x20,0x20,0x3E,0x22,0x22,0x3E],
            '历': [0x02,0x02,0x7E,0x20,0x3E,0x22,0x22,0x3E],
            '任': [0x7E,0x40,0x40,0x7E,0x42,0x42,0x7E],
            '务': [0x7E,0x40,0x40,0x7E,0x42,0x42,0x7E],
            '列': [0x7E,0x40,0x40,0x7E,0x42,0x42,0x7E],
            '表': [0x7E,0x40,0x40,0x7E,0x42,0x42,0x7E],
            '完': [0x7E,0x40,0x40,0x7E,0x42,0x42,0x7E],
            '成': [0x7E,0x40,0x40,0x7E,0x42,0x42,0x7E],
            ' ': [0x00,0x00,0x00,0x00,0x00,0x00,0x00],
            ':': [0x00,0x18,0x18,0x00,0x18,0x18,0x00],
            '/': [0x02,0x04,0x08,0x10,0x20,0x40,0x00],
            '-': [0x00,0x00,0x00,0x7E,0x00,0x00,0x00],
            '.': [0x00,0x00,0x00,0x00,0x00,0x18,0x18],
            '(': [0x0C,0x10,0x20,0x20,0x20,0x10,0x0C],
            ')': [0x30,0x08,0x04,0x04,0x04,0x08,0x30],
        }
        chars = list(text)
        cx = x
        for ch in chars:
            if ch in font:
                glyph = font[ch]
                for row in range(8):
                    rowdata = glyph[row] if row < len(glyph) else 0
                    for col in range(7):
                        if rowdata & (0x40 >> col):
                            if 0 <= cx+col < SCREEN_W and 0 <= y+row < SCREEN_H:
                                os.lseek(self.fd, (y+row) * SCREEN_STRIDE + cx+col, os.SEEK_SET)
                                os.write(self.fd, bytes([color]))
            cx += 9

    def flip(self):
        log('FB.flip: calling eips')
        os.system("eips -c > /dev/null 2>&1")
        log('FB.flip: done')

class TouchInput:
    def __init__(self):
        log('Touch: opening /dev/input/event1')
        self.fd = open("/dev/input/event1", "rb")
        self.touch_x = None
        self.touch_y = None
        self.touch_down = False
        self.touch_start_x = None

    def read_event(self):
        while True:
            if select.select([self.fd], [], [], 0.1)[0]:
                data = self.fd.read(16)
                if len(data) < 16:
                    continue
                ts_sec, ts_usec, t_type, code, value = struct.unpack("IIHHI", data)
                if t_type == EV_ABS:
                    if code == ABS_MT_POSITION_X:
                        self.touch_x = value
                    elif code == ABS_MT_POSITION_Y:
                        self.touch_y = value
                    elif code == ABS_MT_TRACKING_ID:
                        if value == 0xFFFFFFFF:
                            if self.touch_start_x is not None and self.touch_x is not None:
                                dx = self.touch_x - self.touch_start_x
                                if abs(dx) > 50:
                                    if dx > 0:
                                        return (self.touch_x, self.touch_y, False, False, True)
                                    else:
                                        return (self.touch_x, self.touch_y, False, True, False)
                                else:
                                    return (self.touch_x, self.touch_y, True, False, False)
                            self.touch_start_x = None
                            self.touch_x = None
                            self.touch_y = None
                        else:
                            self.touch_start_x = self.touch_x
            else:
                return (None, None, False, False, False)

    def close(self):
        self.fd.close()

def fetch_tasks():
    log('fetch_tasks: start')
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("192.168.10.7", 8082))
        request = "GET /api/events HTTP/1.1\r\nHost: 192.168.10.7\r\n\r\n"
        sock.send(request.encode())
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        sock.close()
        body = response.split(b"\r\n\r\n")[1]
        tasks = json.loads(body)
        pending = [t for t in tasks if not t.get("completed", False)]
        log(f'fetch_tasks: got {len(pending)} tasks')
        return pending
    except Exception as e:
        log(f'fetch_tasks: error {e}')
        return []

log('=== App Starting ===')

fb = Framebuffer()
fb.clear()
fb.flip()
log('Screen cleared')

log('Drawing header...')
fb.fill_rect(0, 0, SCREEN_W, 60, BLACK)
fb.draw_text(20, 20, 'Task', 24, WHITE)
fb.flip()
log('Header drawn')

log('Fetching tasks...')
tasks = fetch_tasks()
log(f'Got {len(tasks)} tasks')

log('Drawing task list...')
y = 80
for i, task in enumerate(tasks[:10]):
    fb.fill_rect(20, y, 560, 50, WHITE if i % 2 == 0 else LIGHT_GRAY)
    fb.draw_text(30, y+5, task.get('title', '')[:20], 18, BLACK)
    y += 60
fb.flip()
log('Task list drawn')

log('Waiting for touch...')
touch = TouchInput()
while True:
    x, y, is_click, is_swipe_left, is_swipe_right = touch.read_event()
    if is_click:
        log(f'Click at x={x}, y={y}')
    time.sleep(0.1)