#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_leftover.py — 找出眨眼后「眼皮区」里残留的暗像素（就是小黑点）。

用法: python blink_leftover.py [expr] [EYE_L|EYE_R] [level]
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
    level = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    geo = B._eye_geometry(arr, box)
    xs, tv, bot, bandT, fillTop = (geo["xs"], geo["top"], geo["bot"],
                                   geo["bandT"], geo["fillTop"])
    bl = B.make_blink(arr.copy(), box, level)
    V = bl[:, :, :3].max(axis=2)

    print("level=%.2f  新出现的暗像素（原图亮、眨眼后暗）:" % level)
    V0 = arr[:, :, :3].max(axis=2)
    x0, y0, x1, y1 = box
    cnt = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if V[y, x] < 120 and V0[y, x] >= 150:
                cnt += 1
                if cnt <= 40:
                    print("   x=%4d y=%4d  V %3d -> %3d  rgb=%s" % (
                        x, y, V0[y, x], V[y, x],
                        tuple(int(q) for q in bl[y, x, :3])))
    print("   合计 %d 个" % cnt)


if __name__ == "__main__":
    main()
