#!/usr/bin/env python3
"""
Kindle E-Ink 显示模块 - Plan A
在真实 Kindle 设备上运行时实现
"""
import os
import subprocess

KINDLE_HOST = os.environ.get("KINDLE_HOST", "192.168.10.72")
KINDLE_KEY = os.environ.get("KINDLE_KEY", "/home/openclaw/.ssh/kindle_key")


def show_image_full(image_path):
    """
    全屏刷新显示图片（GC16 模式，清残影）
    """
    # SCP 传图
    subprocess.run([
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, image_path,
        f"root@{KINDLE_HOST}:/tmp/calendar_frame.png"
    ], check=True, capture_output=True)

    # 显示
    subprocess.run([
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, f"root@{KINDLE_HOST}",
        "killall -STOP cvm; eips -c; eips -g /tmp/calendar_frame.png -w GC16 -f; killall -CONT cvm"
    ], check=True, capture_output=True)


def show_image_partial(image_path):
    """
    局部刷新显示图片（不清残影）
    """
    subprocess.run([
        "scp", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, image_path,
        f"root@{KINDLE_HOST}:/tmp/calendar_frame.png"
    ], check=True, capture_output=True)

    subprocess.run([
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", KINDLE_KEY, f"root@{KINDLE_HOST}",
        f"eips -g /tmp/calendar_frame.png"
    ], check=True, capture_output=True)
