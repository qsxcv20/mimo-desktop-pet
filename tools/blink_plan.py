#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_plan.py — 打印 make_blink 每一列的决策值（不实际渲染）。

用法: python blink_plan.py [expr] [level] [EYE_L|EYE_R]
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


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    level = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    which = sys.argv[3] if len(sys.argv) > 3 else "EYE_L"

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    geo = B._eye_geometry(arr, box)
    if geo is None:
        print("geometry=None")
        return
    xs = geo["xs"]
    n = len(xs)
    print("expr=%s %s level=%s  工作区 x[%d..%d] n=%d" % (
        expr, which, level, xs[0], xs[-1], n))
    print("   x   lashT lashB  openB  d   newLT newLB  fill[ft..fb)  fw   skin条")
    for k in range(0, n, 4):
        x = int(xs[k])
        lid = int(round(geo["lashB"][k]))
        bot = int(round(geo["openB"][k]))
        lt = int(round(geo["lashT"][k]))
        lb = int(round(geo["lashB"][k]))
        edge = min(k, n - 1 - k)
        fw = 1.0 if edge >= 16 else edge / 16.0
        fw = fw * fw * (3.0 - 2.0 * fw)
        d = int(round(level * (bot - lid) * fw))
        new_lb = lid + d
        new_lt = new_lb - (lb - lt)
        ft = max(box[1], lt)
        fb = new_lt
        print("%5d %6d %6d %6d %4d %6d %6d  %5d..%-5d  %.2f  h=%d" % (
            x, lt, lb, bot, d, new_lt, new_lb, ft, fb, fw, geo["stripH"][k]))


if __name__ == "__main__":
    main()
