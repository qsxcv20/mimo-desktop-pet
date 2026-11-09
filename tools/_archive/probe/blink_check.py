#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_check.py — 把眨眼帧和非眨眼帧的眼睛区域并排放大，直观验证眨眼方向。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

ROOT = r"D:\桌面宠物"
SHEET = os.path.join(ROOT, "build", "mimo-witch", "spritesheet.png")
OUT = os.path.join(ROOT, "_mimo", "blink-check.png")

COLS = 24
FRAME = 256

im = Image.open(SHEET).convert("RGBA")
FW = im.width // COLS

# idle 行：眨眼帧在 13/14/15（半闭 -> 全闭 -> 睁开）
picks = [(0, "f0 睁眼"), (12, "f12 睁眼"), (13, "f13 半闭"),
         (14, "f14 全闭"), (15, "f15 睁开"), (16, "f16 睁眼")]

cell_w, cell_h = FW, FW
label_h = 30
canvas = Image.new("RGBA", (cell_w * len(picks), cell_h + label_h),
                    (244, 244, 248, 255))
d = ImageDraw.Draw(canvas)

for i, (c, lab) in enumerate(picks):
    fr = im.crop((c * FW, 0, (c + 1) * FW, FW))
    canvas.alpha_composite(fr, (i * cell_w, label_h))
    d.text((i * cell_w + 8, 8), lab, fill=(20, 20, 20, 255))

canvas.convert("RGB").save(OUT)
print("->", OUT)

# 再单独放大眼睛区域（idle 行 f13/f14/f15）
import numpy as np
arr = np.array(im)
FWf = FW
EYE_BOX = (0.20, 0.34, 0.80, 0.56)      # 帧内比例
big = Image.new("RGBA", (900, 620), (246, 246, 250, 255))
db = ImageDraw.Draw(big)
for i, c in enumerate((0, 13, 14, 15)):
    fr = arr[0:FWf, c * FWf:(c + 1) * FWf]
    x0 = int(EYE_BOX[0] * FWf); x1 = int(EYE_BOX[2] * FWf)
    y0 = int(EYE_BOX[1] * FWf); y1 = int(EYE_BOX[3] * FWf)
    sub = Image.fromarray(fr[y0:y1, x0:x1]).resize((int((x1 - x0) * 2.4),
                                                    int((y1 - y0) * 2.4)),
                                                   Image.LANCZOS)
    big.alpha_composite(sub, (i * 225 + 6, 40))
    db.text((i * 225 + 6, 14), "f%d" % c, fill=(20, 20, 20, 255))
OUT2 = os.path.join(ROOT, "_mimo", "blink-zoom.png")
big.convert("RGB").save(OUT2)
print("->", OUT2)
