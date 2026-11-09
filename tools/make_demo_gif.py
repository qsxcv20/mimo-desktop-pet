#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""make_demo_gif.py — 把四套表情并排合成一个 GIF，方便一眼看出动画差异。"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
from PIL import Image, ImageDraw, ImageFont

SRC = r"D:\桌面宠物\build\mimo-witch\spritesheet.webp"
OUT = r"D:\桌面宠物\build\mimo-witch\_demo-all.gif"
EXPRESSIONS = ["idle", "happy", "think", "tired"]
LABELS = ["idle 待机", "happy 完成", "think 思考", "tired 出错"]
COLS, ROWS = 24, 4
BG = (244, 244, 248, 255)

sheet = Image.open(SRC).convert("RGBA")
FW = sheet.width // COLS
FH = sheet.height // ROWS

cell_w, cell_h = FW, FH
label_h = 26
canvas = Image.new("RGBA", (cell_w * 4, cell_h + label_h), BG)
d = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
except Exception:
    font = ImageFont.load_default()
for i, lab in enumerate(LABELS):
    d.text((i * cell_w + 8, 4), lab, fill=(60, 48, 40, 255), font=font)

frames = []
for c in range(COLS):
    f = Image.new("RGBA", canvas.size, BG)
    for r in range(len(EXPRESSIONS)):
        fr = sheet.crop((c * FW, r * FH, (c + 1) * FW, (r + 1) * FH))
        f.alpha_composite(fr, (r * cell_w, label_h))
    frames.append(f.convert("P", palette=Image.ADAPTIVE, colors=128))

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=100,
               loop=0, optimize=True, disposal=2)
print("GIF ->", OUT, frames[0].size)
