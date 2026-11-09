#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""crop.py — 按 union 坐标裁剪原画并放大。

用法: python crop.py [expr] x0 y0 x1 y1 [scale] [out.png]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import numpy as np

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1]
    x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]
    scale = float(sys.argv[6]) if len(sys.argv) > 6 else 4.0
    out = sys.argv[7] if len(sys.argv) > 7 else os.path.join(
        B.OUT, "crop-%s-%d_%d.png" % (expr, x0, y0))

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    sub = arr[y0:y1, x0:x1]
    img = Image.fromarray(sub).convert("RGB")
    w, h = img.size
    img = img.resize((int(w * scale), int(h * scale)), Image.NEAREST)
    img.save(out)
    print("-> %s  %dx%d  src=(%d,%d)-(%d,%d) scale=%s" %
          (out, img.size[0], img.size[1], x0, y0, x1, y1, scale))


if __name__ == "__main__":
    main()
