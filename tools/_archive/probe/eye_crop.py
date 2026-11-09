#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_crop.py — 把眼部框按原分辨率放大导出，肉眼看结构。

用法: python eye_crop.py [expr] [EYE_L|EYE_R] [scale] [out.png]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import numpy as np

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(
        B.OUT, "eye-crop-%s-%s.png" % (expr, which))

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    x0, y0, x1, y1 = getattr(B, which)
    sub = arr[y0:y1, x0:x1]
    img = Image.fromarray(sub).convert("RGB")
    w, h = img.size
    img = img.resize((int(w * scale), int(h * scale)), Image.NEAREST)
    img.save(out)
    print("-> %s  %dx%d (box=%s scale=%s)" % (out, img.size[0], img.size[1],
                                             (x0, y0, x1, y1), scale))


if __name__ == "__main__":
    main()
