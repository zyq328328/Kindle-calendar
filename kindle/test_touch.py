#!/usr/bin/env python3
"""测试触摸坐标映射"""

W = 800
RIGHT_W = 60
LEFT_W = 120

def rot_coord(x_phys, y_phys):
    """物理600x800 → 渲染800x600"""
    return 800 - y_phys, x_phys

# 测试一些典型的触摸位置
test_points = [
    (0, 0),      # 物理左上角
    (600, 0),    # 物理右上角
    (0, 800),    # 物理左下角
    (600, 800),  # 物理右下角
    (300, 400),  # 物理中心
    (100, 200),  # 物理左侧
    (500, 600),  # 物理右侧
]

print("物理坐标 → 渲染坐标")
print("-" * 30)
for x_phys, y_phys in test_points:
    x_rot, y_rot = rot_coord(x_phys, y_phys)
    in_nav = "导航栏" if x_rot >= W - RIGHT_W else "内容区"
    print(f"({x_phys:4d}, {y_phys:4d}) → ({x_rot:4d}, {y_rot:4d}) [{in_nav}]")

# 测试待办区域的y坐标计算
print("\n待办区域y坐标计算:")
y = 20 + 45 + 30 + 5 * 25 + 10 + 30
print(f"待办项起始y: {y}")

# 测试第一个待办项的位置
box_x = LEFT_W + 30
box_y = y
print(f"第一个待办项 □ 位置: ({box_x}, {box_y})")
