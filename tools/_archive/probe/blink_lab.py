#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_lab.py — 眨眼效果实验台。

直接在原画上按不同 level 画眨眼，横向拼成一条，方便快速比对。
不改精灵图也能看效果。

用法: python blink_lab.py [expr] [out.png]
     expr: idle / think / tired / happy
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402

LEVELS = [0.0, 0.35, 0.60, 0.80, 1.0]


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    out = sys.argv[2] if len(sys.argv) > 2 else \
        r"D:\桌面宠物\_mimo\blink-lab.png"

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    full = Image.open(path).convert("RGBA").crop(B.UNION_BBOX)
    arr = np.array(full)

    crops = []
    for lvl in LEVELS:
        a = arr.copy()
        a = B.make_blink(a, B.EYE_L, lvl)
        a = B.make_blink(a, B.EYE_R, lvl)
        # 两只眼一起裁出来
        x0 = min(B.EYE_L[0], B.EYE_R[0])
        x1 = max(B.EYE_L[2], B.EYE_R[2])
        y0 = min(B.EYE_L[1], B.EYE_R[1])
        y1 = max(B.EYE_L[3], B.EYE_R[3])
        c = Image.fromarray(a[y0:y1, x0:x1]).convert("RGB")
        crops.append(c)
        print("  level=%.2f -> 裁剪 %dx%d" % (lvl, c.width, c.height))

    w = max(c.width for c in crops)
    h = sum(c.height for c in crops) + 6 * (len(crops) - 1)
    sheet = Image.new("RGB", (w, h), (255, 255, 255))
    y = 0
    for c in crops:
        sheet.paste(c, (0, y))
        y += c.height + 6
    sheet.save(out)
    print("-> %s  %dx%d  (自上而下 level=%s)"
          % (out, sheet.width, sheet.height, LEVELS))


if __name__ == "__main__":
    main()
