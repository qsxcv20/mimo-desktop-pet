#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_cols.py — 打印 make_blink 输出（2048 空间）逐列的色块剖面。

用法: python blink_cols.py [expr] [level] [x0] [x1] [y0] [y1] [step]
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def cls(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    s = 0 if mx == 0 else (mx - mn) * 255 // mx
    if v < 80:
        return "#"          # 深棕/黑
    if s < 22 and v >= 243:
        return "W"          # 纯白
    if s < 40 and v >= 232:
        return "w"          # 浅灰/极浅肤
    if s < 75 and v >= 215:
        return "."          # 皮肤
    if r > 200 and g > 120 and b < 140:
        return "O"          # 橙/黄
    if r > g > b and r - b > 50:
        return "o"          # 暗橙
    return "?"


def runs(arr, x, y0, y1):
    out = []
    prev = None
    st = y0
    for y in range(y0, y1):
        c = cls(int(arr[y, x, 0]), int(arr[y, x, 1]), int(arr[y, x, 2]))
        if c != prev:
            if prev is not None:
                out.append((prev, st, y - 1))
            prev, st = c, y
    out.append((prev, st, y1 - 1))
    return out


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "think"
    level = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    x0 = int(sys.argv[3]) if len(sys.argv) > 3 else 690
    x1 = int(sys.argv[4]) if len(sys.argv) > 4 else 760
    y0 = int(sys.argv[5]) if len(sys.argv) > 5 else 985
    y1 = int(sys.argv[6]) if len(sys.argv) > 6 else 1170
    step = int(sys.argv[7]) if len(sys.argv) > 7 else 4

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    base = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    out = B.make_blink(base.copy(), B.EYE_L, level)

    print("expr=%s level=%s  x %d..%d  y %d..%d" % (expr, level, x0, x1, y0, y1))
    for x in range(x0, x1, step):
        rr = runs(out, x, y0, y1)
        s = " | ".join("%s:%d-%d" % (c, a, b) for c, a, b in rr if b - a >= 1)
        print("x=%4d  %s" % (x, s))


if __name__ == "__main__":
    main()
