#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import traceback

print("Testing font loading...")

font_paths = [
    "/usr/java/lib/fonts/Bookerly-Regular.ttf",
    "/usr/java/lib/fonts/Amazon-Ember-Regular.ttf",
]

for font_path in font_paths:
    try:
        font = ImageFont.truetype(font_path, 24)
        print(f"✓ Success: {font_path}")
        
        # Test Chinese rendering
        img = Image.new('L', (200, 50), 255)
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "测试中文", font=font, fill=0)
        print(f"  - Chinese rendering works")
        
    except Exception as e:
        print(f"✗ Failed: {font_path}")
        print(f"  Error: {e}")
        traceback.print_exc()

print("\nTesting default font...")
try:
    font = ImageFont.load_default()
    print(f"✓ Default font loaded")
except Exception as e:
    print(f"✗ Default font failed: {e}")
