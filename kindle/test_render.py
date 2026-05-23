#!/usr/bin/env python3
"""
渲染测试工具 - 测试日历渲染功能是否正常

使用方法：
    ssh 连接到 Kindle 后执行:
    python3 test_render.py

作用：
    1. 从服务器获取日历事件数据
    2. 渲染首页视图到 /tmp/test.png
    3. 输出渲染结果和事件数量

注意：
    1. 需要在 Kindle 设备上运行
    2. 需要确保服务器端正常运行
    3. 渲染成功后可查看 /tmp/test.png 验证效果
    
调试用途：
    当日历出现白屏或假死时，可运行此脚本检查：
    - 是否能成功获取事件数据
    - 是否能正常渲染图片
    - 是否有编码错误或字体问题
"""
import calendar_renderer

print("Fetching events...")
events = calendar_renderer.fetch_events()
print(f"Fetched {len(events)} events")

print("Rendering frame...")
calendar_renderer.render_frame('home', '2026-05-23', events, '/tmp/test.png')
print("Rendered successfully")