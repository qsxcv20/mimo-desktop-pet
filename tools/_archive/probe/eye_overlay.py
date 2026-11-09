#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_overlay.py — 把检测到的几何曲线画到放大的眼部图上。

用法: python eye_overlay.py [expr] [EYE_L|EYE_R] [out.png]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image, ImageDraw

import build_anim_sheet as B  # noqa: E402

OUT_DIR = r"D:\桌面宠物\_mimo"
ZOOM = 3
PAD = 30


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        OUT_DIR, "eye-overlay-%s-%s.png" % (expr, which))

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    img = Image.open(path).convert("RGBA").crop(B.UNION_BBOX)
    geo = B._eye_geometry(np.array(img), getattr(B, which))
    if geo is None:
        print("geometry = None")
        return

    x0, y0, x1, y1 = getattr(B, which)
    cx0, cy0 = max(0, x0 - PAD), max(0, y0 - PAD)
    cx1, cy1 = min(img.width, x1 + PAD), min(img.height, y1 + PAD)
    crop = img.crop((cx0, cy0, cx1, cy1)).resize(
        ((cx1 - cx0) * ZOOM, (cy1 - cy0) * ZOOM), Image.LANCZOS)
    bg = Image.new("RGBA", crop.size, (235, 235, 238, 255))
    bg.alpha_composite(crop)
    d = ImageDraw.Draw(bg)

    def P(x, y):
        return ((x - cx0) * ZOOM, (y - cy0) * ZOOM)

    xs = geo["xs"]
    top = geo["top"]
    bot = geo["bot"]
    bandT = geo["bandT"]
    pts_lid = [P(x, top[k]) for k, x in enumerate(xs)]
    pts_bot = [P(x, bot[k]) for k, x in enumerate(xs)]
    pts_band = [P(x, bandT[k]) for k, x in enumerate(xs)]
    d.line(pts_lid, fill=(0, 200, 255, 255), width=2)       # 睑缘
    d.line(pts_bot, fill=(0, 90, 255, 255), width=2)        # 眼球下沿
    d.line(pts_band, fill=(255, 220, 0, 255), width=2)     # 睫毛带上沿

    # 完全闭眼时的新睑缘
    pts_new = [P(x, top[k] + (bot[k] - top[k])) for k, x in enumerate(xs)]
    d.line(pts_new, fill=(255, 0, 0, 255), width=2)

    # 填充区（level=1.0）：半透明红
    ov = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for k, x in enumerate(xs):
        ft = int(geo["fillTop"][k])
        lid = int(round(top[k]))
        nlid = int(round(top[k] + (bot[k] - top[k])))
        od.rectangle([P(x, ft)[0], P(x, ft)[1], P(x, nlid)[0], P(x, nlid)[1]],
                     fill=(255, 0, 0, 70))
    bg = Image.alpha_composite(bg, ov)
    d = ImageDraw.Draw(bg)
    d.line(pts_lid, fill=(0, 200, 255, 255), width=2)       # 睑缘
    d.line(pts_bot, fill=(0, 90, 255, 255), width=2)        # 眼球下沿
    d.line(pts_band, fill=(255, 220, 0, 255), width=2)     # 睫毛带上沿

    # 采样点
    for k, x in enumerate(xs):
        if k % 6 == 0:
            d.ellipse([P(x, top[k])[0] - 3, P(x, top[k])[1] - 3,
                       P(x, top[k])[0] + 3, P(x, top[k])[1] + 3],
                      fill=(0, 200, 255, 255))

    bg.convert("RGB").save(out)
    print("-> %s" % out)
    print("睑缘 y: %s" % [int(v) for v in top[::6]])
    print("bandT : %s" % [int(v) for v in bandT[::6]])
    print("下沿  : %s" % [int(v) for v in bot[::6]])
    print("x 范围: %d..%d" % (xs[0], xs[-1]))


if __name__ == "__main__":
    main()
