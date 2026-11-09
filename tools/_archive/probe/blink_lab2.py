#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_lab2.py — 单眼眨眼实验台（放大）。

用法: python blink_lab2.py [expr] [EYE_L|EYE_R] [out.png] [scale]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402

LEVELS = [0.0, 0.35, 0.60, 1.0]


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    out = sys.argv[3] if len(sys.argv) > 3 else r"D:\桌面宠物\_mimo\blink-lab2.png"
    scale = float(sys.argv[4]) if len(sys.argv) > 4 else 1.4

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)

    crops = []
    for lvl in LEVELS:
        a = B.make_blink(arr.copy(), box, lvl)
        x0, y0, x1, y1 = box
        c = Image.fromarray(a[y0 - 40:y1 + 20, x0:x1]).convert("RGB")
        c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
        crops.append(c)

    w = max(c.width for c in crops)
    h = sum(c.height for c in crops) + 8 * (len(crops) - 1)
    sheet = Image.new("RGB", (w, h), (245, 245, 245))
    y = 0
    for c in crops:
        sheet.paste(c, (0, y))
        y += c.height + 8
    sheet.save(out)
    print("-> %s  %dx%d  %s  level=%s" % (out, sheet.width, sheet.height,
                                          which, LEVELS))


if __name__ == "__main__":
    main()
