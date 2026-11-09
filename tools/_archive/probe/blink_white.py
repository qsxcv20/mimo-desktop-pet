#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_white.py — 找出眨眼结果里「原图暗、结果却发白」的像素（白条/白斑）。

用法: python blink_white.py [expr] [EYE_L|EYE_R] [level]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "think"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    level = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    geo = B._eye_geometry(arr, box)
    xs, tv, bv, raw, ft = (geo["xs"], geo["top"], geo["bot"], geo["raw"],
                           geo["fillTop"])
    bl = B.make_blink(arr.copy(), box, level)
    V0 = arr[:, :, :3].max(axis=2)
    V1 = bl[:, :, :3].max(axis=2)
    x0, y0, x1, y1 = box
    hit = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if V1[y, x] > 235 and V0[y, x] < 200:
                hit.append((x, y))
    print("level=%.2f  发白残留 %d 个" % (level, len(hit)))
    cols = {}
    for x, y in hit:
        cols.setdefault(x, []).append(y)
    print("  按列:")
    for x in sorted(cols):
        k = int(np.searchsorted(xs, x))
        k = min(k, len(xs) - 1)
        d = int(round(level * (bv[k] - tv[k])))
        print("   x=%4d  y=%s   lid=%4d lt=%4d raw=%4d ft=%4d d=%4d" % (
            x, "%d..%d" % (min(cols[x]), max(cols[x])),
            int(round(tv[k])), int(round(raw[k])), int(round(raw[k])),
            int(round(ft[k])), d))


if __name__ == "__main__":
    main()
