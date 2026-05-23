#!/usr/bin/env python3
"""
Kindle 触摸输入模块 - Plan A
在真实 Kindle 设备上运行时实现
"""
import os
import struct
import select as sel

EVENT_DEVICE = os.environ.get("EVENT_DEVICE", "/dev/input/event1")
ABS_X = 53
ABS_Y = 54
EV_ABS = 3


def wait_for_touch(timeout_ms=5000):
    """
    等待触摸事件，返回 (x, y) 坐标
    超时返回 None
    """
    try:
        fd = os.open(EVENT_DEVICE, os.O_RDONLY | os.O_NONBLOCK)
    except Exception as e:
        print(f"[touch_input] Cannot open {EVENT_DEVICE}: {e}")
        return None

    x_val = None
    y_val = None

    try:
        poll_obj = sel.poll()
        poll_obj.register(fd, sel.POLLIN)
        events = poll_obj.poll(timeout_ms)

        if not events:
            return None

        while True:
            try:
                data = os.read(fd, 16)
                if len(data) < 16:
                    break
                tv_sec, tv_usec, ev_type, code, value = struct.unpack("iiHHi", data)
                if ev_type == EV_ABS:
                    if code == ABS_X:
                        x_val = value
                    elif code == ABS_Y:
                        y_val = value
            except Exception:
                break
    finally:
        os.close(fd)

    if x_val is not None and y_val is not None:
        return (x_val, y_val)
    return None
