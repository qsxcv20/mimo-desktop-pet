#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""debug_blink_out.py — 检查 make_blink 输出的像素，确认「白块」到底是什么。"""
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
    lvl = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    row = int(sys.argv[4]) if len(sys.argv) > 4 else 1050

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    out = B.make_blink(arr.copy(), box, lvl)
    x0, y0, x1, y1 = box
    print("原图 row=%d:" % row)
    print("  " + " ".join("%3d" % out[row, x, 0] for x in range(x0, x0 + 120, 4)))
    print("原图 row=%d (g):" % row)
    print("  " + " ".join("%3d" % out[row, x, 1] for x in range(x0, x0 + 120, 4)))
    print("原图 row=%d (b):" % row)
    print("  " + " ".join("%3d" % out[row, x, 2] for x in range(x0, x0 + 120, 4)))
    print("\n对应 x: " + " ".join("%3d" % x for x in range(x0, x0 + 120, 4)))


if __name__ == "__main__":
    main()
