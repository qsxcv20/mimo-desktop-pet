#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""skin_probe.py — 采样眼睛周围几个位置的颜色。

用法: python skin_probe.py [expr] [EYE_L|EYE_R]
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
    x0, y0, x1, y1 = getattr(B, which)

    pts = [
        ("脸上-右", 790, 1040),
        ("脸上-右下", 800, 1120),
        ("脸上-左上", 620, 980),
        ("眼皮条", 700, 1000),
        ("眼下皮肤", 710, 1178),
        ("眼下皮肤2", 640, 1140),
        ("眼右外侧", 790, 1080),
    ]
    print("expr=%s %s box=%s" % (expr, which, (x0, y0, x1, y1)))
    for name, x, y in pts:
        patch = arr[y - 3:y + 4, x - 3:x + 4, :3].reshape(-1, 3)
        med = np.median(patch.astype(np.float32), axis=0)
        print("  %-10s (%4d,%4d) = %s" % (name, x, y,
                                          [int(v) for v in med]))


if __name__ == "__main__":
    main()
