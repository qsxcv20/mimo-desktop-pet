#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""grid_parts.py — 在 UNION_BBOX 坐标系上打网格，用来标注各部件区域。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
from PIL import Image, ImageDraw

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "assets", "src")
UNION_BBOX = (35, 27, 2009, 1879)
OUT = os.path.join(ROOT, "_mimo", "grid-parts.png")

im = Image.open(os.path.join(SRC, "mimo-idle-v2@2048.png")).convert("RGBA")
im = im.crop(UNION_BBOX)
bg = Image.new("RGBA", im.size, (245, 245, 248, 255))
bg.alpha_composite(im)
d = ImageDraw.Draw(bg)
W, H = bg.size

# 每 100px 一条线，每 500px 加粗
for x in range(0, W, 100):
    major = (x % 500 == 0)
    d.line([(x, 0), (x, H)], fill=(0, 160, 255, 190 if major else 90),
           width=3 if major else 1)
    if x % 200 == 0:
        d.text((x + 4, 4), str(x), fill=(0, 90, 200, 255))
for y in range(0, H, 100):
    major = (y % 500 == 0)
    d.line([(0, y), (W, y)], fill=(255, 0, 160, 190 if major else 90),
           width=3 if major else 1)
    if y % 200 == 0:
        d.text((4, y + 4), str(y), fill=(200, 0, 120, 255))

bg.convert("RGB").resize((W // 2, H // 2), Image.LANCZOS).save(OUT)
print("网格图 ->", OUT, "(原始 %dx%d, 显示半尺寸)" % (W, H))
print("UNION_BBOX =", UNION_BBOX, " W=%d H=%d" % (W, H))
