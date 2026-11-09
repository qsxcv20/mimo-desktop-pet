#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_parts.py — 用 alpha 连通域找出可以和主体分离、单独摆动的部件。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "assets", "src")
UNION_BBOX = (35, 27, 2009, 1879)

im = Image.open(os.path.join(SRC, "mimo-idle-v2@2048.png")).convert("RGBA")
im = im.crop(UNION_BBOX)
a = np.array(im)
alpha = a[..., 3]
print("union size:", im.size, " alpha>128 占比: %.1f%%"
      % (100.0 * (alpha > 128).mean()))

try:
    import cv2
except Exception:
    print("需要 opencv")
    sys.exit(1)

mask = (alpha > 128).astype(np.uint8)
n, labels, stats, cents = cv2.connectedComponentsWithStats(mask, 8)
print("连通域数量:", n - 1)
order = np.argsort(-stats[1:, cv2.CC_STAT_AREA]) + 1
for i in order[:12]:
    x = stats[i, cv2.CC_STAT_LEFT]
    y = stats[i, cv2.CC_STAT_TOP]
    w = stats[i, cv2.CC_STAT_WIDTH]
    h = stats[i, cv2.CC_STAT_HEIGHT]
    area = stats[i, cv2.CC_STAT_AREA]
    if area < 300:
        continue
    print("  #%-2d area=%-8d bbox=(%4d,%4d,%4d,%4d)  中心=(%4d,%4d)"
          % (i, area, x, y, w, h, cents[i][0], cents[i][1]))

# 导出前 6 大连通域的单独图，方便肉眼确认哪个是耳朵
out_dir = os.path.join(ROOT, "_mimo", "parts")
os.makedirs(out_dir, exist_ok=True)
for rank, i in enumerate(order[:6]):
    if stats[i, cv2.CC_STAT_AREA] < 300:
        continue
    sub = np.zeros_like(a)
    sub[labels == i] = a[labels == i]
    p = os.path.join(out_dir, "cc%d_area%d.png" % (rank, stats[i, cv2.CC_STAT_AREA]))
    Image.fromarray(sub).save(p)
    print("  导出", p)
