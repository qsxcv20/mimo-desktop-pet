#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""lash_profile.py — 打印指定列的纵向像素剖面（找睫毛带顶边的尖刺）。

用法: python lash_profile.py [expr] [EYE_L|EYE_R] [x1] [x2]
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
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_R"
    x1 = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    x2 = int(sys.argv[4]) if len(sys.argv) > 4 else 1115
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    geo = B._eye_geometry(arr, box)
    xs, tv, bot, bandT, fillTop = (geo["xs"], geo["top"], geo["bot"],
                                   geo["bandT"], geo["fillTop"])
    V = arr[:, :, :3].max(axis=2)

    print("睑缘/带顶（几何解）:")
    for k, x in enumerate(xs):
        if x1 <= x <= x2:
            print("  x=%4d lid=%4d bandT=%4d fillTop=%4d raw=%4d" % (
                x, int(round(tv[k])), int(round(bandT[k])),
                int(round(fillTop[k])), int(round(geo["raw"][k]))))

    print("\n纵向剖面 (V<150 记为 #, 亮记为 .):")
    for x in range(x1, x2 + 1, 2):
        row = ""
        for y in range(960, 1070):
            row += "#" if V[y, x] < 150 else "."
        print("x=%4d %s" % (x, row))


if __name__ == "__main__":
    main()
