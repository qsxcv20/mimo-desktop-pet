#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_cols.py — 打印眼睛框内**每一列**的原始测量值和有效性判定。

用法: python eye_cols.py [expr] [EYE_L|EYE_R] [x0] [x1]
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
    expr = sys.argv[1] if len(sys.argv) > 1 else "think"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    x0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    x1 = int(sys.argv[4]) if len(sys.argv) > 4 else 0

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    if x0 <= 0:
        x0 = box[0]
    if x1 <= 0:
        x1 = box[2]
    geo = B._eye_geometry(arr, box)
    if geo is None:
        print("geometry = None")
        return
    ac = geo["allcols"]
    xs = geo["xs"]
    inwork = set(int(v) for v in xs)
    print("expr=%s %s box=%s  工作区 x[%d..%d]" % (
        expr, which, box, xs[0], xs[-1]))
    print("  x   openT openB  lashT lashB  gap 厚  有效性")
    for x in range(x0, x1):
        if x not in ac:
            print("%5d   ---- 无眼球 ----" % x)
            continue
        ot, ob, lt, lb = ac[x]
        gap = ot - lb if lb >= 0 else -1
        ok = []
        if lt < 0:
            ok.append("无睫毛")
        else:
            if lb > ot - 1:
                ok.append("睫在眼下")
            if gap > 45:
                ok.append("gap>45")
            if (ob - ot) < 5:
                ok.append("太矮")
        mark = "OK" if not ok else ",".join(ok)
        star = "*" if x in inwork else " "
        print("%s%4d %6d %6d %6d %6d %5d %3d  %s" % (
            star, x, ot, ob, lt, lb, gap, lb - lt + 1 if lb >= 0 else -1, mark))


if __name__ == "__main__":
    main()
