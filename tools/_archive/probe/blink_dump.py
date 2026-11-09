#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_dump.py — 打印眨眼过程中用到的颜色与填充范围。

用法: python blink_dump.py [expr] [EYE_L|EYE_R]
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
    geo = B._eye_geometry(arr, box)
    if geo is None:
        print("geometry None")
        return
    xs, top, bot, bandT = geo["xs"], geo["top"], geo["bot"], geo["bandT"]
    skin, under = geo["skin"], geo["under"]

    print(" x   lid   bot    lt    d=1.0  上眼皮色        下眼睑色      原图[lt-3]     原图[lt+40]")
    for k, x in enumerate(xs):
        if k % 8:
            continue
        lid = int(round(top[k]))
        b = int(round(bot[k]))
        lt = int(round(bandT[k]))
        d = b - lid
        orig_lt = tuple(int(q) for q in arr[max(0, lt - 3), x, :3])
        orig_mid = tuple(int(q) for q in arr[min(arr.shape[0] - 1, lt + 40), x, :3])
        print("%4d %5d %5d %5d %6d  %-15s %-15s %-15s %s" % (
            x, lid, b, lt, d,
            tuple(int(q) for q in skin[k]),
            tuple(int(q) for q in under[k]),
            orig_lt, orig_mid))


if __name__ == "__main__":
    main()
