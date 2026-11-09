#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""crop_eyes.py — 裁出眼睛区域放大，确认lash 线（闭合线）在框内的位置。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "assets", "src")
UNION_BBOX = (35, 27, 2009, 1879)
EYE_L = (595, 962, 842, 1170)
EYE_R = (862, 958, 1207, 1170)

im = Image.open(os.path.join(SRC, "mimo-idle-v2@2048.png")).convert("RGBA")
im = im.crop(UNION_BBOX)

out = os.path.join(ROOT, "_mimo", "eyes-detail.png")
canvas = Image.new("RGBA", (1600, 620), (240, 240, 244, 255))
d = ImageDraw.Draw(canvas)

for i, (name, box) in enumerate((("EYE_L", EYE_L), ("EYE_R", EYE_R))):
    x0, y0, x1, y1 = box
    eh = y1 - y0
    ew = x1 - x0
    crop = im.crop(box)
    sc = 2.0
    crop = crop.resize((int(ew * sc), int(eh * sc)), Image.LANCZOS)
    cx = i * 790 + 10
    canvas.alpha_composite(crop, (cx, 40))
    # 在框内按比例画参考线
    for frac in (0.05, 0.10, 0.16, 0.22, 0.24, 0.30, 0.40, 0.50, 0.60,
                 0.62, 0.66, 0.70, 0.74, 0.78, 0.82, 0.90, 1.00):
        yy = 40 + int(eh * sc * frac)
        col = (0, 160, 255, 210) if frac < 0.9 else (230, 0, 160, 210)
        d.line([(cx, yy), (cx + int(ew * sc), yy)], fill=col)
        d.text((cx + 4, yy - 14), "%.2f" % frac, fill=col[:3] + (255,))
    d.text((cx, 12), "%s  box=(%d,%d,%d,%d)  %dx%d"
           % (name, x0, y0, x1, y1, ew, eh), fill=(20, 20, 20, 255))

canvas.convert("RGB").save(out)
print("->", out)
print("框内比例参考线已画：0.05 ~ 0.60（蓝线）")
