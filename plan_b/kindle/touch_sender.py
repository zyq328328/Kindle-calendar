#!/usr/bin/env python3
"""
Kindle 触摸 HTTP 发送器（方案B）
检测 home screen 触摸区域，POST 坐标到服务端
"""

import os
import sys
import time
import signal
import struct
import subprocess
from pathlib import Path

# 目标服务端（方案B，已废弃）
SERVER_URL = os.environ.get("SERVER_URL", "http://192.168.10.7:8082/touch")

# 触摸设备
EVENT_DEVICE = "/dev/input/event1"

# home screen 触摸区域定义
# Kindle 7 屏幕 600x800，右下角 100x100 区域，触发日历触摸
TRIGGER_X_MIN = 500
TRIGGER_X_MAX = 600
TRIGGER_Y_MIN = 700
TRIGGER_Y_MAX = 800


def unlock_touch_input():
    """
    SIGSTOP Xorg+awesome 解锁 event1
    """
    pids = []
    for name in ["Xorg", "awesome"]:
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True, text=True
            )
            pids.extend(result.stdout.strip().split())
        except Exception:
            pass

    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGSTOP)
            print(f"[touch_sender] SIGSTOP sent to {name} (PID {pid})")
        except Exception as e:
            print(f"[touch_sender] Failed to SIGSTOP {name}: {e}")

    # 等待一小段时间确保事件被释放
    time.sleep(0.3)


def lock_touch_input():
    """
    SIGCONT 恢复 Xorg+awesome
    """
    pids = []
    for name in ["Xorg", "awesome"]:
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True, text=True
            )
            pids.extend(result.stdout.strip().split())
        except Exception:
            pass

    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGCONT)
            print(f"[touch_sender] SIGCONT sent to {name} (PID {pid})")
        except Exception as e:
            print(f"[touch_sender] Failed to SIGCONT {name}: {e}")


def read_touch_event():
    """
    用 select.poll() 读取触摸事件
    返回 (x, y) 或 None
    """
    try:
        fd = os.open(EVENT_DEVICE, os.O_RDONLY | os.O_NONBLOCK)
    except Exception as e:
        print(f"[touch_sender] Cannot open {EVENT_DEVICE}: {e}")
        return None

    # event1: 16 bytes little-endian iiHHI (Kindle 7 is 32-bit ARM)
    #   timeval: sec(4) + usec(4) = 8 bytes
    #   type(2) + code(2) + value(4) = 8 bytes
    # Kindle zforce2: ABS_X=53, ABS_Y=54
    ABS_X = 53
    ABS_Y = 54
    EV_ABS = 3

    x_val = None
    y_val = None
    poll_obj = None

    try:
        import select as sel
        poll_obj = sel.poll()
        poll_obj.register(fd, sel.POLLIN)

        # 等待最多 2 秒
        events = poll_obj.poll(2000)

        if not events:
            print("[touch_sender] No touch event within 2s")
            return None

        # 读取所有待处理事件，取最后一个坐标
        while True:
            try:
                data = os.read(fd, 16)  # 每次读一个完整事件（16 bytes）
                if len(data) < 16:
                    break
                # iiHHi: sec(4) + usec(4) + type(2) + code(2) + value(4)
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
        if poll_obj:
            poll_obj.unregister(fd)

    if x_val is not None and y_val is not None:
        return (x_val, y_val)
    return None


def post_touch(x, y, action="tap"):
    """
    POST 到服务端，优先用 requests，fallback 到 urllib
    """
    payload = {
        "x": int(x),
        "y": int(y),
        "action": action
    }

    try:
        import requests
        resp = requests.post(SERVER_URL, json=payload, timeout=2)
        print(f"[touch_sender] POST {SERVER_URL} -> {resp.status_code}")
        return resp.ok
    except ImportError:
        # Kindle 可能没有 requests，用 urllib fallback
        import json as json_mod, urllib.request
        data = json_mod.dumps(payload).encode("utf-8")
        req = urllib.request.Request(SERVER_URL, data=data,
                                    headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                print(f"[touch_sender] POST {SERVER_URL} -> {resp.status}")
                return True
        except Exception as e:
            print(f"[touch_sender] urllib POST failed: {e}")
            return False
    except Exception as e:
        print(f"[touch_sender] POST failed: {e}")
        return False


def in_trigger_zone(x, y):
    """检查坐标是否在触发区域"""
    return (TRIGGER_X_MIN <= x <= TRIGGER_X_MAX and
            TRIGGER_Y_MIN <= y <= TRIGGER_Y_MAX)


def main():
    print("[touch_sender] Starting Kindle touch HTTP sender (plan B)")

    # 解锁触摸输入
    unlock_touch_input()

    # 读取触摸事件
    coord = read_touch_event()

    if coord is None:
        print("[touch_sender] No valid touch detected")
        lock_touch_input()
        sys.exit(0)

    x, y = coord
    print(f"[touch_sender] Touch at ({x}, {y})")

    # 检查是否在触发区域
    if not in_trigger_zone(x, y):
        print(f"[touch_sender] ({x},{y}) not in trigger zone, skipping POST")
        lock_touch_input()
        sys.exit(0)

    # POST 到服务端
    post_touch(x, y)

    # 恢复触摸输入
    lock_touch_input()

    print("[touch_sender] Done")


if __name__ == "__main__":
    main()
