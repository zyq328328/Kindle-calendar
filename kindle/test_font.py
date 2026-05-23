#!/usr/bin/env python3
"""
字体测试工具 - 快速测试指定字体是否支持中文

使用方法：
    ssh 连接到 Kindle 后执行:
    python3 test_font.py

作用：
    1. 测试 Kindle 自带的 Bookerly 和 Amazon-Ember 字体
    2. 验证这些字体是否能正确渲染中文字符
    3. 输出简单的 SUCCESS/FAILED 结果

注意：
    需要在 Kindle 设备上运行，依赖 PIL 库
"""
from PIL import Image, ImageDraw, ImageFont

test_fonts = [
    "/usr/java/lib/fonts/Bookerly-Regular.ttf",
    "/usr/java/lib/fonts/Amazon-Ember-Regular.ttf",
]

for font_path in test_fonts:
    try:
        font = ImageFont.truetype(font_path, 24)
        img = Image.new('L', (200, 50), 255)
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "测试中文", font=font, fill=0)
        print(f"SUCCESS: {font_path} supports Chinese")
    except Exception as e:
        print(f"FAILED: {font_path} - {e}")