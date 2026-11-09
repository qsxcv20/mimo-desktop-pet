#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_geom.py — 打印新眨眼模型解出的几何。

用法: python eye_geom.py [expr] [EYE_L|EYE_R] [step]
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
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 6

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    geo = B._eye_geometry(arr, box)
    print("expr=%s %s box=%s" % (expr, which, box))
    if geo is None:
        print("geometry = None  (-> 这一套不眨眼)")
        return
    xs = geo["xs"]
    n = len(xs)
    print("列数 n=%d  x[%d..%d]" % (n, xs[0], xs[-1]))
    print("  x    睑缘  下沿  高度  睫顶  睫底  睫厚")
    for k in range(0, n, step):
        print("%5d %5d %5d %5d %5d %5d %5d" % (
            xs[k], geo["openT"][k], geo["openB"][k],
            geo["openB"][k] - geo["openT"][k],
            geo["lashT"][k], geo["lashB"][k], geo["lashW"][k]))
    print("cBase=%s" % np.round(geo["cBase"], 1).tolist())
    d = geo["dbg"]
    print("脸皮中位=%s  眼皮中位=%s  眼窝中位=%s  脸皮像素数=%d" % (
        np.round(d[0], 1).tolist(), np.round(d[1], 1).tolist(),
        np.round(d[2], 1).tolist(), d[3]))
    h = geo["openB"] - geo["openT"]
    print("高度: 首=%d 末=%d 中=%d 最大=%d" % (h[0], h[-1], h[n // 2], h.max()))
    raw = geo["raw"]
    print("\n原始值（前 12 / 后 12 列）：x  openT openB lashT lashB")
    for k in list(range(min(12, n))) + list(range(max(0, n - 12), n)):
        print("%5d  %6d %6d %6d %6d" % (xs[k], raw[0][k], raw[1][k],
                                        raw[2][k], raw[3][k]))


if __name__ == "__main__":
    main()
