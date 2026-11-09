#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_probe.py — 逐列探针：看眨眼算法到底能检测到哪些列。

用法: python blink_probe.py [expr] [EYE_L|EYE_R]
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

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    x0, y0, x1, y1 = box

    iris = B._find_iris(arr, box)
    print("box   =", box)
    if iris is None:
        print("iris  = None")
        return
    ix0, ix1, iy0, iy1, _ = iris
    print("iris  = ix[%d..%d] iy[%d..%d]" % (ix0, ix1, iy0, iy1))

    cols = B._eye_structure(arr, box, ix0, ix1, iy0, iy1)
    if cols is None:
        print("cols  = None")
        return
    xs = [c[0] for c in cols]
    print("cols  = n=%d  x[%d..%d]   (box x[%d..%d])" %
          (len(cols), min(xs), max(xs), x0, x1))
    print("      未被检测到的列 = %d / %d" % (x1 - x0 - len(cols), x1 - x0))

    # 哪些列被跳过、为什么
    got = {c[0] for c in cols}
    print("\n--- 逐列诊断（x, V@iy0-1, lash_top, lash_bot, eye_bottom, skin, lash） ---")
    for x in range(x0, x1, 8):
        seg = arr[y0:y1, x, :3].astype(np.int16)
        V = seg.max(axis=1)
        yy = iy0 - 1
        vtop = int(V[yy - y0]) if 0 <= yy - y0 < len(V) else -1
        if x in got:
            c = [c for c in cols if c[0] == x][0]
            print("x=%4d  V@%d=%3d  top=%4d bot=%4d ebot=%4d  skin=%s lash=%s" % (
                x, yy, vtop, c[1], c[2], c[5],
                tuple(int(v) for v in c[3]), tuple(int(v) for v in c[4])))
        else:
            # 找原因
            reason = "?"
            if yy < y0 + 2:
                reason = "iy0 太靠上"
            elif vtop >= 140:
                reason = "V@iy0-1>=140 (非睫毛)"
            else:
                reason = "其他"
            print("x=%4d  V@%d=%3d  -- 跳过: %s" % (x, yy, vtop, reason))

    # 填充区 bbox（level=1.0）
    mid = cols[len(cols) // 2]
    D = max(8, mid[5] - mid[2])
    print("\nmid col = x=%d top=%d bot=%d ebot=%d  D=%d" %
          (mid[0], mid[1], mid[2], mid[5], D))
    print("完全闭眼时填充区 = x[%d..%d]  y[top .. top+D]" % (min(xs), max(xs)))


if __name__ == "__main__":
    main()
