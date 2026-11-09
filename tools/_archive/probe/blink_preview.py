#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_preview.py — 快速预览眨眼各阶段（只处理眼睛区域，秒级出图）。

用法: python blink_preview.py
输出: _mimo/blink-preview.png
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_anim_sheet import (make_blink, EYE_L, EYE_R, UNION_BBOX,
                              SOURCE_FILE, SRC)

ROOT = r"D:\桌面宠物"
OUT = os.path.join(ROOT, "_mimo", "blink-preview.png")

LEVELS = [("睁眼 0.00", None), ("微眯 0.30", 0.30), ("半闭 0.60", 0.60),
          ("全闭 1.00", 1.00), ("半闭 0.60", 0.60)]

im = Image.open(os.path.join(SRC, SOURCE_FILE["idle"])).convert("RGBA")
im = im.crop(UNION_BBOX)
arr = np.array(im)

SC = 2.4
rows = []
for label, lvl in LEVELS:
    a = arr if lvl is None else make_blink(arr, EYE_L, lvl)
    if lvl is not None:
        a = make_blink(a, EYE_R, lvl)
    pil = Image.fromarray(a)
    crops = []
    for box in (EYE_L, EYE_R):
        c = pil.crop(box)
        w = c.width * SC
        h = c.height * SC
        crops.append(c.resize((int(w), int(h)), Image.LANCZOS))
    rows.append((label, crops))

cw = int((EYE_L[2] - EYE_L[0]) * SC)
ch = int((EYE_L[3] - EYE_L[1]) * SC)
gap = 16
label_w = 110
canvas = Image.new("RGBA", (label_w + (cw * 2 + gap) + 20,
                             30 + (ch + 22) * len(rows)), (246, 246, 250, 255))
d = ImageDraw.Draw(canvas)
for i, (label, crops) in enumerate(rows):
    y = 26 + i * (ch + 22)
    d.text((10, y + ch // 2 - 8), label, fill=(30, 30, 30, 255))
    canvas.alpha_composite(crops[0], (label_w, y))
    canvas.alpha_composite(crops[1], (label_w + cw + gap, y))

canvas.convert("RGB").save(OUT)
print("->", OUT, canvas.size)
