#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""face_grid3.py — 统一裁剪框下的脸部区域网格图，用来人工读眼睛坐标。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

SRC = r"D:\桌面宠物\assets\src"
EXPRS = ["idle", "happy", "think", "tired"]

imgs = {n: Image.open(os.path.join(SRC, "mimo-%s-v2@2048.png" % n)).convert("RGBA")
        for n in EXPRS}
boxes = [imgs[n].getchannel("A").getbbox() for n in EXPRS]
union = (min(b[0] for b in boxes), min(b[1] for b in boxes),
         max(b[2] for b in boxes), max(b[3] for b in boxes))
crops = {n: imgs[n].crop(union) for n in EXPRS}
W, H = crops["idle"].size
print("union size", W, H)

# 脸部区域网格图
x0, y0, x1, y1 = 500, 820, 1300, 1200
step = 50
for name in ("idle", "think"):
    c = crops[name].crop((x0, y0, x1, y1)).convert("RGB")
    s = 2
    c = c.resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    for gx in range(x0 - x0 % step, x1 + 1, step):
        px = (gx - x0) * s
        d.line([(px, 0), (px, c.height)], fill=(255, 0, 255), width=1)
        d.text((px + 2, 2), str(gx), fill=(255, 0, 255))
    for gy in range(y0 - y0 % step, y1 + 1, step):
        py = (gy - y0) * s
        d.line([(0, py), (c.width, py)], fill=(0, 160, 255), width=1)
        d.text((2, py + 2), str(gy), fill=(0, 120, 255))
    out = r"D:\桌面宠物\_mimo\grid-%s.png" % name
    c.save(out)
    print("->", out, c.size)
