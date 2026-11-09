#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""dark_runs.py — 逐列列出所有「暗色段」，并给出亮度，用来区分睫毛和虹膜暗轮廓。

用法: python dark_runs.py [expr] [EYE_L|EYE_R] [step]
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
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    x0, y0, x1, y1 = getattr(B, which)
    V = arr[:, :, :3].max(axis=2)

    print("expr=%s %s  box=%s" % (expr, which, (x0, y0, x1, y1)))
    print("列内的暗色段 (V<150)： y0-y1  厚度  平均V  平均RGB")
    for x in range(x0, x1, step):
        col = V[:, x]
        runs = []
        y = y0
        while y < y1:
            if col[y] < 150:
                s = y
                while y < y1 and col[y] < 150:
                    y += 1
                if y - s >= 3:
                    runs.append((s, y - 1))
            else:
                y += 1
        if not runs:
            continue
        parts = []
        for s, e in runs:
            patch = arr[s:e + 1, x, :3].astype(np.float32)
            mv = float(V[s:e + 1, x].mean())
            rgb = [int(v) for v in patch.mean(axis=0)]
            parts.append("%d-%d(%d V%.0f %s)" % (s, e, e - s + 1, mv, rgb))
        print("x=%4d %s" % (x, "  ".join(parts)))


if __name__ == "__main__":
    main()
