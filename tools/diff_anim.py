#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""diff_anim.py — 量化精灵图的帧间差异，并生成差分热力图。

差异太小 = 看起来僵硬。这是「灵动」与否的客观指标。
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
import numpy as np
from PIL import Image

SHEET = r"D:\桌面宠物\build\mimo-witch\spritesheet.png"
OUT = r"D:\桌面宠物\_mimo\anim-diff.png"
EXPRESSIONS = ["idle", "happy", "think", "tired"]

im = Image.open(SHEET).convert("RGBA")
W, H = im.size
COLS, ROWS = 24, 4
FW = W // COLS
FH = H // ROWS
arr = np.array(im)

print("精灵图 %dx%d  帧 %dx%d  列 %d" % (W, H, FW, FH, COLS))
print()
print("%-8s %10s %10s %10s %10s" % ("表情", "平均帧差", "最大帧差", "活跃像素%", "垂直位移px"))
print("-" * 56)

heat = Image.new("RGB", (COLS * 40, ROWS * 40), (28, 28, 34))
import PIL.ImageDraw
dr = PIL.ImageDraw.Draw(heat)

for r, expr in enumerate(EXPRESSIONS):
    frames = []
    for c in range(COLS):
        f = arr[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW]
        frames.append(f.astype(np.int16))
    diffs = []
    for c in range(COLS):
        a = frames[c]
        b = frames[(c + 1) % COLS]
        d = np.abs(a - b).mean(axis=2)
        diffs.append(d)
        # 画热力块
        dr.rectangle([c * 40, r * 40, c * 40 + 38, r * 40 + 38],
                     fill=(min(255, int(d.mean() * 6)),
                               min(255, int(d.mean() * 4)), 60))
    allm = np.stack(diffs)
    mean_d = float(allm.mean())
    max_d = float(allm.max())
    active = float((allm > 6).mean() * 100)
    # 垂直位移：alpha 质心在两帧间的变化
    ys = []
    for c in range(COLS):
        a = frames[c][..., 3]
        idx = np.arange(a.shape[0])[:, None]
        tot = a.sum()
        ys.append(float((a * idx).sum() / tot) if tot else 0.0)
    ys = np.array(ys)
    print("%-8s %10.2f %10.2f %10.1f %10.2f"
          % (expr, mean_d, max_d, active, float(ys.max() - ys.min())))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
heat.save(OUT)
print("\n差分热力图 ->", OUT)
