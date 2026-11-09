#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_eye_col.py — 打印原画某一列眼睛区域的纵向像素结构。

用来精确定位：眉毛 / 上睫毛 / 虹膜顶 / 虹膜底 / 下睫毛。
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
    x = int(sys.argv[2]) if len(sys.argv) > 2 else 710
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    full = Image.open(path).convert("RGBA").crop(B.UNION_BBOX)
    arr = np.array(full)

    box = B.EYE_L
    x0, y0, x1, y1 = box
    ya = int(sys.argv[3]) if len(sys.argv) > 3 else y0
    yb = int(sys.argv[4]) if len(sys.argv) > 4 else y1
    print("列 x=%d （框 %s）  y=%d..%d" % (x, str(box), ya, yb))
    for y in range(ya, yb):
        r, g, b, a = [int(v) for v in arr[y, x]]
        mark = ""
        if a < 128:
            mark = " (透明)"
        print("  y=%4d  rgb=(%3d,%3d,%3d) a=%3d%s" % (y, r, g, b, a, mark))


if __name__ == "__main__":
    main()
