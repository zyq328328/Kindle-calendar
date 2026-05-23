#!/usr/bin/env python3
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
