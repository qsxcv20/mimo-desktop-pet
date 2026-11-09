#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_zoom.py — 把眨眼结果的某个源区域放大到极致。

用法: python blink_zoom.py [expr] [EYE_L|EYE_R] [level] [x0] [y0] [x1] [y1] [zoom] [out]
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
    level = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
    x0 = int(sys.argv[4]) if len(sys.argv) > 4 else 980
    y0 = int(sys.argv[5]) if len(sys.argv) > 5 else 975
    x1 = int(sys.argv[6]) if len(sys.argv) > 6 else 1040
    y1 = int(sys.argv[7]) if len(sys.argv) > 7 else 1025
    zoom = int(sys.argv[8]) if len(sys.argv) > 8 else 10
    out = sys.argv[9] if len(sys.argv) > 9 else r"D:\桌面宠物\_mimo\blink-zoom.png"

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    bl = B.make_blink(arr.copy(), box, level)

    crops = [("原图", arr), ("眨眼 %.2f" % level, bl)]
    ims = []
    for name, a in crops:
        im = Image.fromarray(a[y0:y1, x0:x1]).convert("RGB")
        im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
        ims.append(im)
    w = max(i.width for i in ims)
    h = sum(i.height for i in ims) + 8
    sheet = Image.new("RGB", (w, h), (250, 250, 250))
    y = 0
    for i in ims:
        sheet.paste(i, (0, y))
        y += i.height + 8
    sheet.save(out)
    print("-> %s  %dx%d  region=(%d,%d,%d,%d) zoom=%d" % (
        out, sheet.width, sheet.height, x0, y0, x1, y1, zoom))


if __name__ == "__main__":
    main()
