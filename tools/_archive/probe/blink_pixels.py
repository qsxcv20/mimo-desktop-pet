#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_pixels.py — 打印 make_blink 之后某一列的逐行颜色。

用法: python blink_pixels.py [expr] [EYE_L|EYE_R] [level] [x] [y0] [y1]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    level = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    x = int(sys.argv[4]) if len(sys.argv) > 4 else 720
    ya = int(sys.argv[5]) if len(sys.argv) > 5 else 980
    yb = int(sys.argv[6]) if len(sys.argv) > 6 else 1160

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    out = B.make_blink(arr.copy(), box, level)

    print("expr=%s %s level=%s x=%d" % (expr, which, level, x))
    print("  y    原画           眨眼后")
    for y in range(ya, yb, 4):
        o = [int(v) for v in arr[y, x, :3]]
        n = [int(v) for v in out[y, x, :3]]
        mark = "  <<<" if o != n else ""
        print("%5d  %-16s %-16s%s" % (y, o, n, mark))


if __name__ == "__main__":
    main()
